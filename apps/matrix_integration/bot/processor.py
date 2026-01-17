from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.botauth.models import MatrixUserBinding
from apps.core.permissions import (
    can_access_patient,
    can_see_patient_in_search,
    can_view_patients,
)
from apps.matrix_integration.models import MatrixBotConversationState, MatrixDirectRoom
from apps.patients.models import Patient, PatientAdmission

from .search import parse_search_query, rank_patient_candidates, search_inpatients


MAX_COMMAND_LENGTH = 200
SELECTION_TIMEOUT = timedelta(minutes=5)


@dataclass
class ProcessingResult:
    action: str
    responses: list
    results_count: int | None = None
    selected_patient_id: str | None = None
    user_id: int | None = None


class BotMessageProcessor:
    def __init__(self, now=None):
        self._now = now or timezone.now

    def handle_message(self, room_id, matrix_user_id, message):
        message = (message or "").strip()
        if not message:
            return ProcessingResult(action="noop", responses=[])

        if len(message) > MAX_COMMAND_LENGTH:
            return ProcessingResult(
                action="input_invalid",
                responses=["Comando muito longo. Limite 200 caracteres."],
            )

        user = MatrixUserBinding.get_user_for_matrix_id(matrix_user_id)
        if not user:
            return ProcessingResult(
                action="unauthorized",
                responses=["Usuario nao autorizado. Fale com o administrador."],
            )

        direct_room = (
            MatrixDirectRoom.objects.filter(room_id=room_id)
            .select_related("user")
            .first()
        )
        if not direct_room or direct_room.user_id != user.id:
            return ProcessingResult(
                action="redirect",
                responses=["Use sua sala privada com o bot."],
                user_id=user.id,
            )

        lower_message = message.lower()
        if lower_message.startswith("!buscar"):
            return self._handle_search(user, room_id, message, "!buscar")
        if lower_message.startswith("/buscar"):
            return self._handle_search(user, room_id, message, "/buscar")

        if message.startswith("!"):
            return ProcessingResult(
                action="help",
                responses=[self._help_message()],
                user_id=user.id,
            )

        if message.startswith("/"):
            return ProcessingResult(
                action="help",
                responses=[self._help_message()],
                user_id=user.id,
            )

        if message.isdigit():
            result = self._handle_selection(user, room_id, message)
            result.user_id = user.id
            return result

        return ProcessingResult(
            action="help",
            responses=[self._help_message()],
            user_id=user.id,
        )

    def _handle_search(self, user, room_id, message, prefix):
        search_text = message[len(prefix) :].strip()
        if not search_text:
            return ProcessingResult(
                action="help",
                responses=[self._help_message()],
                user_id=user.id,
            )

        if not can_view_patients(user):
            return ProcessingResult(
                action="permission_denied",
                responses=["Voce nao tem permissao para buscar pacientes."],
                user_id=user.id,
            )

        query = parse_search_query(search_text)
        if not (query.name_terms or query.record_number or query.bed or query.ward):
            return ProcessingResult(
                action="help",
                responses=[self._help_message()],
                user_id=user.id,
            )

        candidates = search_inpatients(query)
        visible = [
            admission
            for admission in candidates
            if can_see_patient_in_search(user, admission.patient)
        ]
        if not visible:
            return ProcessingResult(
                action="patient_search",
                responses=["Nenhum paciente encontrado."],
                results_count=0,
                user_id=user.id,
            )

        ranked = rank_patient_candidates(visible, query)[:5]
        patient_ids = [str(admission.patient_id) for admission in ranked]

        MatrixBotConversationState.objects.update_or_create(
            room_id=room_id,
            defaults={
                "user": user,
                "state": MatrixBotConversationState.State.SELECTING_PATIENT,
                "data": {"patient_ids": patient_ids},
            },
        )

        response = self._format_search_results(query, ranked)
        return ProcessingResult(
            action="patient_search",
            responses=[response],
            results_count=len(ranked),
            user_id=user.id,
        )

    def _handle_selection(self, user, room_id, message):
        state = MatrixBotConversationState.objects.filter(room_id=room_id).first()
        if not state:
            return ProcessingResult(
                action="selection_missing",
                responses=["Nenhuma selecao ativa. Use /buscar."],
                user_id=user.id,
            )
        if state.user_id != user.id:
            return ProcessingResult(
                action="redirect",
                responses=["Use sua sala privada com o bot."],
                user_id=user.id,
            )
        if state.updated_at < self._now() - SELECTION_TIMEOUT:
            state.delete()
            return ProcessingResult(
                action="selection_expired",
                responses=["Selecao expirada. Use /buscar novamente."],
                user_id=user.id,
            )

        patient_ids = state.data.get("patient_ids", []) if state.data else []
        if not message.isdigit():
            return ProcessingResult(
                action="selection_invalid",
                responses=["Selecao invalida. Responda com o numero da lista."],
                user_id=user.id,
            )

        index = int(message) - 1
        if index < 0 or index >= len(patient_ids):
            return ProcessingResult(
                action="selection_invalid",
                responses=["Selecao invalida. Responda com o numero da lista."],
                user_id=user.id,
            )

        patient = Patient.objects.filter(id=patient_ids[index]).first()
        if not patient:
            return ProcessingResult(
                action="selection_invalid",
                responses=["Paciente nao encontrado. Use /buscar novamente."],
                user_id=user.id,
            )

        admission = (
            PatientAdmission.objects.filter(patient=patient, is_active=True)
            .order_by("-admission_datetime")
            .first()
        )
        if not admission:
            return ProcessingResult(
                action="selection_invalid",
                responses=["Paciente nao encontrado. Use /buscar novamente."],
                user_id=user.id,
            )

        if not can_access_patient(user, patient):
            return ProcessingResult(
                action="permission_denied",
                responses=["Voce nao tem permissao para acessar este paciente."],
                user_id=user.id,
            )

        state.delete()
        response = self._format_patient_details(patient, admission)
        return ProcessingResult(
            action="patient_select",
            responses=[response],
            selected_patient_id=str(patient.id),
            user_id=user.id,
        )

    def _format_search_results(self, query, admissions):
        criteria_parts = []
        if query.name_terms:
            criteria_parts.append(f"Nome: {' '.join(query.name_terms)}")
        if query.record_number:
            criteria_parts.append(f"Registro: {query.record_number}")
        if query.bed:
            criteria_parts.append(f"Leito: {query.bed}")
        if query.ward:
            criteria_parts.append(f"Ala: {query.ward}")

        lines = []
        if criteria_parts:
            lines.append("Busca por: " + " | ".join(criteria_parts))

        count = len(admissions)
        lines.append(f"Encontrados {count} paciente(s):")
        for idx, admission in enumerate(admissions, start=1):
            patient = admission.patient
            bed = admission.initial_bed or admission.final_bed or patient.bed or "-"
            ward_obj = admission.ward or patient.ward
            ward_label = "-"
            if ward_obj:
                ward_label = ward_obj.abbreviation or ward_obj.name
            lines.append(f"{idx}) {patient.name} (Leito {bed}, Ala {ward_label})")

        lines.append("Responda com o numero da lista.")
        return "\n".join(lines)

    def _format_patient_details(self, patient, admission):
        birthdate = "-"
        if patient.birthday:
            birthdate = patient.birthday.strftime("%d/%m/%Y")
        gender = patient.get_gender_display()
        record_number = patient.get_current_record_number() or "-"
        admission_date = "-"
        stay_days = "-"
        if admission.admission_datetime:
            admission_date = admission.admission_datetime.strftime("%d/%m/%Y")
            stay_days = (self._now().date() - admission.admission_datetime.date()).days

        lines = [
            f"Paciente: {patient.name}",
            f"Nascimento: {birthdate}",
            f"Sexo: {gender}",
            f"Registro: {record_number}",
            f"Admissao: {admission_date}",
            f"Permanencia: {stay_days} dias",
        ]
        return "\n".join(lines)

    def _help_message(self):
        return (
            "Use !buscar com nome, registro, leito ou ala.\n"
            "Exemplos:\n"
            "!buscar Joao Silva\n"
            "!buscar reg:12345\n"
            "!buscar leito:101 enf:uti"
        )
