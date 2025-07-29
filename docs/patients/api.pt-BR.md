# Documentação da API JSON de Pacientes

## Endpoints Disponíveis

### Endpoints de Informações de Pacientes

- `GET /patients/api/search/` - Busca pacientes com parâmetros de consulta
- `GET /patients/api/record-numbers/{patient_id}/` - Obtém histórico de números de prontuário do paciente
- `GET /patients/api/admissions/{patient_id}/` - Obtém histórico de internações do paciente
- `GET /patients/api/record-lookup/{record_number}/` - Encontra paciente por número de prontuário
- `GET /patients/api/admission/{admission_id}/` - Obtém detalhes da internação

## Autenticação

Todos os endpoints da API requerem autenticação. Os usuários devem estar logados através da autenticação de sessão do Django.

## Campos de Dados do Paciente

### Campos Principais do Paciente

- `id` - Identificador UUID do paciente
- `name` - Nome completo do paciente
- `gender` - Sexo do paciente (M=Masculino, F=Feminino, O=Outro, N=Não Informado)
- `gender_display` - Valor do sexo legível para humanos
- `current_record_number` - Número de prontuário hospitalar atual
- `status` - Status do paciente (internado, ambulatorial, emergência, alta, transferido, óbito)
- `is_currently_admitted` - Booleano indicando status de internação atual
- `bed` - Atribuição de leito atual (se aplicável)
- `healthcard_number` - Número do cartão de saúde
- `phone` - Telefone de contato

## Exemplos

### Busca de Pacientes

```bash
curl -b sessionid=seu-session-id \
  "http://example.com/patients/api/search/?q=João&page=1&per_page=20"
```

Resposta inclui informações de sexo:
```json
{
  "results": [
    {
      "id": "uuid-aqui",
      "name": "João Silva",
      "gender": "M",
      "gender_display": "Masculino",
      "current_record_number": "12345",
      "status": "Internado"
    }
  ]
}
```

### Números de Prontuário do Paciente

```bash
curl -b sessionid=seu-session-id \
  "http://example.com/patients/api/record-numbers/uuid-aqui/"
```

Resposta inclui informações de sexo:
```json
{
  "patient_id": "uuid-aqui",
  "patient_name": "João Silva",
  "gender": "M",
  "gender_display": "Masculino",
  "current_record_number": "12345",
  "records": [...]
}
```