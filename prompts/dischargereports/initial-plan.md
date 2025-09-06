# Discharge Report - Initial Plan

I need to implement a new feature app in this project called "dischargereports".

## It should have the following fields

- admission date - date
- discharge date - date
- admissionHistory - text
- problemsAndDiagnosis - text
- examsList - text
- proceduresList - text
- inpatientMedicalHistory - text
- dischargeStatus - text
- dischargeRecommendations - text
- medicalSpecialty - text
- isDraft - boolean
- specialty - text

## Main features

- should extend the Event model and have its own event type
- must be editable and deletable as long as it is a draft, after that it should follow the default event permissions constraints
- draft=true should be the default value
- the create and the edit templates should have the options to save as draft or save definitly
- must have its own partial event-card to be used when rendering in the timeline
- must have its own filtering option in the timeline template
- must have the default CRUD templates, like @apps/dailynotes and @apps/simplenotes
- should have a separate editing template for update, do not reuse the create template
- should have similar methods as dailynotes, historyahdphysicals and simplenotes like this fragment of dailynotes model:

```python
    def save(self, *args, **kwargs):
        """Override save to set the correct event type."""
        self.event_type = Event.DAILY_NOTE_EVENT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Return the absolute URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_detail', kwargs={'pk': self.pk})

    def get_edit_url(self):
        """Return the edit URL for this daily note."""
        from django.urls import reverse
        return reverse('apps.dailynotes:dailynote_update', kwargs={'pk': self.pk})

    def __str__(self):
        """String representation of the daily note."""
        return f"Evolução - {self.patient.name} - {self.event_datetime.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        verbose_name = "Evolução"
        verbose_name_plural = "Evoluções"
        ordering = ["-event_datetime"]
```

- should have a create pdf option, like the one in the @apps/outppatientprescriptions
  @apps/outppatientprescriptions/templates/outppatientprescriptions/outppatientprescriptions_print.html,
  which should generate a pdf file in Brazilian portuguese with the following sections/data in this sequence:
  . Header in every page with: hospital name and icon in the top center, followed by the text "Relatório de Alta" and
  the specialty name. Followed by the patient identification (name, current record number, birthday, gender, age, admission
  date, discharge date)
  . problems and diagnosis
  . admission history
  . exams list
  . procedures list
  . inpatient medical history
  . discharge status
  . discharge recommendations
  . current date and time and the name of the user that generated the report at the bottom of the page

  If this report is bigger than on page, it should indicate the pagination at the top right or bottom right as such:
  . for a 2 page report: "Page 1 of 2" and "Page 2 of 2" or "Page 1/2" and "Page 2/2"

## Management Commands

You should create a management command to import data from the legacy firebase app, much like the @apps/core/management/commands/sync_firebase_data.py does. The root reference in that database for the discharge reports is called "patientDischargeReports".

This command should also create an AdmissionRecord for each imported report pair of admission and discharge dates.

You should add documentation to run this command as a docker compose command.

A typical firebase discharge report record has this structure:

```json
{
  "content": {
    "admissionDate": "2025-08-22",
    "admissionHistory": "Paciente, 68 anos, com histórico de AVCs isquêmicos prévios com hemiparesia direita (sequela de AVCi 2024) admitido em contexto de alteração comportamental súbita, eversão ocular e liberação esfincteriana  seguida de cefalía, cervicalgia e queda da propria altura. Paciente fazia uso prévio de AAS, sendo suspenso por médico assistente devido quadro de bicitopenia, com plaqueta na faixa de 26.000.\n\nPaciente foi investigado pela neurologia e  admitido em jul/25 por novo déficit acompanhado de crise convulsiva como abertura de novo quadro além de evidência em TAC de crânio (08/07) de áreas de encefalomalácea no cerebelo direito e região parietal esquerda; de aspecto sequelar e AngioTC de crânio e carótidas (09/07) evidenciando estenose de cerca de 50% e placa ulcerada tendo TOAST atribuido a ateromatose de grandes vasos.\nSolicitada avaliação da Cirurgia Vascular quanto a possibilidades cirúrgicas e indicada Correção Endovascular.\n",
    "dischargeDate": "2025-09-05",
    "dischargeRecommendations": "1) Retorno no Ambulatório de hemodinâmica em 15-20 dias.\n2) Procurar a Emergência do HGRS ou a UPA mais próxima da residência com o relatório de alta em caso de quaisquer intercorrências, como febre, queda do estado geral ou dor importante\n3) Manter as medicações em uso previamente\n4) Usar as medicações prescritas na receita anexa\n5) Trazer o Doppler de carótidas no retorno\n6) Manter uso de DAP por 6 meses, conforme orientado na alta hospitalar\n",
    "examsList": "# Exames. Complementares:\n- LAB 02/09: Trop 0,006; CKMB 1,5; Hb 9,9; leuco 8330 sd; plaq 180000; RNI 1,03; TTPA 30s; Ur 48; Cr 1; Na 136; K 4,6; Ca 9,1; Mg 1,8; P 4,3; BT 0,8; PCR 3\n\n- Tomografia de crânio (12/08/25): Achados relevantes: Segue com áreas de encefalomalácea no cerebelo direito e região parietal esquerda; de aspecto sequelar. Melhor evidenciada pequena hipodensidade cortico subcortical na região frontal esquerda, podendo estar relacionado a injúria isquêmica recente. Demais achados: Hipoatenuação na substância branca periventricular, relacionada a focos de gliose/desmielinização.Tronco cerebral com morfologia, contornos e valores de atenuação normais .Acentuação dos sulcos corticais e fissuras encefálicas associado à dilatação compensatória do sistema ventricular supratentorial, inferindo redução volumétrica encefálica.Não há evidências de processos expansivos intracranianos infra ou supra-tentoriais. Ausência de hemorragias intracranianas.Estruturas da linha média centradas. Calcificações parietais ateromatosas nas artérias carótidas internas.\n\n- EDA 09/08: Úlceras gástricas Sakita  A1// Forrest IIc\n\n- Tomografia de crânio (09/07/25): Presença de encefalomalácia em região cerebelar a direita e occiptoparietal a esquerda, com formação hipodensa em região de lobo frontal a esquerda, evidenciando insulto isquêmico agudo/sugabudo.\n\n- Tomografia de crânio (08/07/25): Segue com áreas de encefalomalácea no cerebelo direito e região parietal esquerda; de aspecto sequelar. \n\nURC (28/07): negativa\n\n- EAS (16/07/25): pH 6.0; densidade 1020; nitrito negativo;  leucócitos 10 por campo; algumas bactérias\n\n- ECOTT( 11/07/25): AE 36mm; FE 44%; hipocinesia difusa.\n\n- TAC de Crânio (08/07): Segue com áreas de encefalomalácea no cerebelo direito e região parietal esquerda; de aspecto sequelar.\n\n- AngioTC de carótidas (10/07): Placa ateromatosa fibrocalcificada de superfície regular, predominando componente de partes moles, em bulbo carotídeo direito que estende-se por cerca de 1,7cm e determina estenose em cerca de 60% na porção proximal da carótida interna direita. Placa ateromatosa com componente de partes moles em bulbo carotídeo esquerdo que estende-se por cerca de 1,3cm e determina estenose em cerca de 50%, destacando-se área com aspecto em adição no aspecto lateral esquerdo/posterior da placa, sugerindo ulceração. Placa ateromatosa com componente de partes moles em terço médio da carótida comum esquerda que estende-se por cerca de 1,0cm, sem determinar estenose significativa.\n",
    "inpatientMedicalHistory": "Paciente evolui em leito de enfermaria, vigil, desorientado conforme padrão prévio, hemodinâmica estável, registros de normocardico, normotenso. Eupneico e confortável em VE, mantendo boa saturimetria periférica. Dieta oral com boa aceitação, sem náuseas ou vômitos. Glicemias controladas. Diurese e dejeções presentes, sem alterações, função renal preservada, sem DHE. Sem exteriorização de sangramentos, queda de Hb compatível com pós operatório. Afebril, sem antibioticoterapia, leuco e PCR sem alterações.\nNega sintomas respiratórios, urinários e gastrointestinais. \n\nAntibioticoterapia:\nMeropenem (03/08 - 13/08)\nVancomicina (06/08 - 14/08)\n\nCULTURAS\nHMC (05/08): Negativa\nURC (16/08): NEGATIVA\n\nAo exame:\nVigil, oscilando episódios de desorientação/agitação, contactante, PIFR.\nHemiparesia à direita. Força muscular grau 4/5. Desvio de rima labial.\nSítio de punção em inguinal direita sem abaulamentos ou hematomas.",
    "patientDischargeStatus": "Paciente recebe alta em bom estado geral, aceitando dieta oral, sem queixas ou intercorrências. Diurese e dejeções presentes, sem alterações. Sem febre, náuseas ou vômitos. Hemodinamicamente estável.\n",
    "problemsAndDiagnostics": "P1. POI (02/09/2025) Angioplastia Carotídea Esquerda com Stent Wallstent 7x40 mm\nP2. AVCi lobo parietal à esquerda aguda/subagudo\n\t» Ictus: incerto com novo deficit 08/07\n\t» TOAST: Aterosclerose de grandes vasos\nP3. AVCis prévio Hemiparesia direita desde 2024\nP4. HAS\nP5. HTLV",
    "proceduresList": "Paciente submetido dia 02/09/2025 a angioplastia carotídea esquerda com stent Wallstent 7x40 mm. Procedimento sem intercorrências. Paciente desperta sem novos déficits neurológicos, mantendo padrão prévio.",
    "specialty": "Cirurgia Vascular"
  },
  "datetime": 1757081600582,
  "patient": "-OVHlG3K_Lvt-GD40xOv",
  "userkey": "z5rdfGIw24PRnbTBbCPfZS7AQRc2",
  "username": "Ane Caroline Carvalho"
}
```

As you can see, the admission and discharge dates are strings in the format 'YYYY-MM-DD' and the dischargereport datetime is in epoch milliseconds.

Fields mapping (original firebase -> this feature app):

- admissionDate -> admission date
- dischargeDate -> discharge date
- admissionHistory -> admissionHistory
- problemsAndDiagnostics -> problemsAndDiagnoses
- examsList -> examsList
- proceduresList -> proceduresList
- inpatientMedicalHistory -> inpatientMedicalHistory
- patientDischargeStatus -> dischargeStatus
- dischargeRecommendations -> dischargeRecommendations
- specialty -> medicalSpecialty

The created_by and updated_by user for all the imported reports should be the first admin user.

The PatientAdmission created should have:

- admission_type as scheduled
- discharge_type as medical
- initial and final beds - empty
- ward - empty
- admission and discharge diagnosis - empty
- stay duration in days should be calculated based on the admission and discharge dates
- is_active should be false

## Structure

You should keep the overall file and folders structure used for other feature apps in this project (see @apps/dailynotes or
@apps/outppatientprescriptions as examples).
Keep the same styling and design used in other feature apps in this project.

## Your mission

Think hard and create a detailed step-by-step plan to implement this feature as a multi phase process, doing your best to use
the sliced development approach. Do not over engineer it. Ask as many clarifying questions as you need before making any
assumptions. After that, write your plan to one or more markdown files at @prompts/dischargereports folder.
