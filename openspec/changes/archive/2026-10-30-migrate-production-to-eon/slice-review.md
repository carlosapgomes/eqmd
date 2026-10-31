# Slice review — migrate-production-to-eon

Registro consolidado dos ciclos de implementação/revisão por slice.
Revisor independente: Pi (gpt-6-luna, think:high), exceto onde
indicado. Fix = ciclos de correção após REVIEW_DEFECTS.

| Slice       | Entrega principal                     | Revisões | Fix |
| ----------- | ------------------------------------- | -------- | --- |
| s1 IPAM     | Reserva <CIDR_RESERVA_EQMD> + validador      | 2        | 1   |
| infra       | Reconciliação inventário (repo infra) | 2        | 1   |
| s2 Compose  | Compose eon + env sintético + gates   | 1        | 1   |
| s3 PG15     | Roles/init/restore + ensaio A→B       | 2        | 2   |
| s4 Frontend | nginx + snippet Caddy + PWA           | 2        | 1   |
| s5 Cron     | UTC + flock + suspensão gated         | 1        | 0   |
| s6 Runbook  | Cutover/rollback/checklist gated      | 3        | 3   |
| s7 Ensaio   | E2E com tempos + fix integração       | 1        | 1   |

Defeitos bloqueantes capturados em revisão (todos resolvidos):
exit-code de input inválido (s1); baseline sem bridge (infra);
migrate com role sem CREATE e template env incompleto (s2/s3);
varredura de cleanup por substring (s4); SQL de freeze inválido,
dump em caminho de container, migrate sem prova de no-op, verificação
parcial de crons, rollback sem mídia reversa (s6 r1); `env_file`
hardcoded no compose e E4 com ownership/ordem errados (s6 r2/r3).
Defeito de integração capturado no ensaio e2e: permissão do
collectstatic no volume (corrigido no compose).

Ensaio final: 4 execuções verdes, 58,06–62,57 s (dados sintéticos;
escala real documentada em `rehearsal-baseline.md`).
