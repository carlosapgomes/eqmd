# Lista de Verificação para Deploy do App Pacientes

## Verificações Pré-Deploy

- [ ] Execute todos os testes e verifique se passaram:
  ```bash
  python manage.py test apps.patients
  ```
- [ ] Verifique se há migrações pendentes:
  ```bash
  python manage.py showmigrations patients
  ```
- [ ] Verifique se as permissões e grupos estão configurados corretamente:
  ```bash
  python manage.py shell -c "from django.contrib.auth.models import Group; print(Group.objects.filter(name__contains='Patient').values('name', 'permissions__codename'))"
  ```
- [ ] Verifique se há avisos de depreciação:
  ```bash
  python -Wd manage.py check patients
  ```

## Passos para Deploy

- [ ] Aplique qualquer migração pendente:
  ```bash
  python manage.py migrate patients
  ```
- [ ] Colete arquivos estáticos:
  ```bash
  python manage.py collectstatic --noinput
  ```
- [ ] Atualize o cache se estiver usando cache:
  ```bash
  python manage.py clear_cache
  ```
- [ ] Reinicie o servidor web:
  ```bash
  sudo systemctl restart gunicorn
  sudo systemctl restart nginx
  ```

## Verificação Pós-Deploy

- [ ] Verifique se o app pacientes está acessível
- [ ] Teste a criação de um novo paciente
- [ ] Teste a criação de registro hospitalar de paciente
- [ ] Verifique se os widgets do dashboard estão sendo exibidos corretamente
- [ ] Verifique se as permissões funcionam corretamente para diferentes funções de usuário
- [ ] Monitore logs de erro para quaisquer problemas:
  ```bash
  tail -f /var/log/nginx/error.log
  tail -f /path/to/django/logs/error.log
  ```