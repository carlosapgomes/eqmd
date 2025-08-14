# Registro de Atividades de Tratamento - LGPD Art. 37

## Informações do Controlador
- **Nome**: [NOME_DO_HOSPITAL]
- **CNPJ**: [CNPJ]
- **Endereço**: [ENDEREÇO_COMPLETO]
- **DPO/Responsável**: [NOME_DPO]
- **Contato DPO**: [EMAIL_DPO] | [TELEFONE_DPO]

---

## 1. DADOS DE PACIENTES

### 1.1 Identificação do Paciente
- **Base Legal**: Art. 11º, II, a (procedimentos médicos)
- **Finalidade**: Identificação e contato para prestação de cuidados médicos
- **Categorias de Dados**: Nome, CPF, data nascimento, endereço, telefone, cartão SUS
- **Origem**: Formulário de cadastro hospitalar, sistema de referência
- **Destinatários**: Equipe médica autorizada, enfermagem, administration
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 20 anos após última consulta (Resolução CFM 1.821/2007)
- **Medidas de Segurança**: Controle de acesso por função, auditoria, criptografia, UUIDs

### 1.2 Dados Médicos Sensíveis  
- **Base Legal**: Art. 11º, II, a (procedimentos médicos)
- **Finalidade**: Registro histórico médico e continuidade tratamento
- **Categorias de Dados**: Diagnósticos, prescrições, exames, evolução clínica, procedimentos
- **Origem**: Registro direto por profissionais de saúde
- **Destinatários**: Médicos responsáveis, equipe multidisciplinar autorizada
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 20 anos após última consulta
- **Medidas de Segurança**: Acesso restrito, logs auditoria, janela edição 24h

---

## 2. DADOS DA EQUIPE MÉDICA

### 2.1 Identificação Profissional
- **Base Legal**: Art. 7º, II (obrigação legal - CFM)
- **Finalidade**: Identificação profissional conforme regulamentação CFM/CRM
- **Categorias de Dados**: Nome, email, CRM, especialidade, telefone
- **Origem**: Cadastro de profissionais, validação CRM
- **Destinatários**: Administração hospitalar, outros profissionais
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 5 anos após fim do vínculo
- **Medidas de Segurança**: Autenticação forte, controle de sessão

---

## 3. DADOS DE AUDITORIA

### 3.1 Logs de Segurança
- **Base Legal**: Art. 7º, VI (interesse legítimo - segurança)
- **Finalidade**: Auditoria de segurança e monitoramento de acesso
- **Categorias de Dados**: Logs de acesso, IP, timestamp, ações realizadas
- **Origem**: Sistema automático de auditoria
- **Destinatários**: Administradores de sistema, DPO
- **Transferências**: Não há transferências internacionais
- **Prazo de Conservação**: 3 anos para investigação de incidentes
- **Medidas de Segurança**: Logs protegidos, acesso restrito, detecção anomalias

---

**Data da Elaboração**: [DATA]  
**Responsável**: [NOME_DPO]  
**Próxima Revisão**: [DATA + 1 ANO]