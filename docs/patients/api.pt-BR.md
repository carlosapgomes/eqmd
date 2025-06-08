# Documentação da API de Pacientes

## Endpoints Disponíveis

### Endpoints de Pacientes

- `GET /api/patients/` - Lista todos os pacientes
- `POST /api/patients/` - Cria um novo paciente
- `GET /api/patients/{id}/` - Recupera um paciente específico
- `PUT /api/patients/{id}/` - Atualiza um paciente
- `DELETE /api/patients/{id}/` - Exclui um paciente

### Endpoints de Registros Hospitalares

- `GET /api/hospital-records/` - Lista todos os registros hospitalares
- `POST /api/hospital-records/` - Cria um novo registro hospitalar
- `GET /api/hospital-records/{id}/` - Recupera um registro hospitalar específico
- `PUT /api/hospital-records/{id}/` - Atualiza um registro hospitalar
- `DELETE /api/hospital-records/{id}/` - Exclui um registro hospitalar

### Endpoints de Tags

- `GET /api/tags/` - Lista todas as tags
- `POST /api/tags/` - Cria uma nova tag
- `GET /api/tags/{id}/` - Recupera uma tag específica
- `PUT /api/tags/{id}/` - Atualiza uma tag
- `DELETE /api/tags/{id}/` - Exclui uma tag

## Autenticação

Todos os endpoints da API requerem autenticação. Use autenticação por token incluindo o token no cabeçalho Authorization:

```
Authorization: Token seu-token-aqui
```

## Exemplos

### Listando Pacientes

```bash
curl -H "Authorization: Token seu-token-aqui" http://example.com/api/patients/
```

### Criando um Paciente

```bash
curl -X POST \
  -H "Authorization: Token seu-token-aqui" \
  -H "Content-Type: application/json" \
  -d '{"name": "João Silva", "birthday": "1990-01-01", "status": 1}' \
  http://example.com/api/patients/
```