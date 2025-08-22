# Development TODOs

This document tracks planned features, improvements, and technical debt for the EquipeMed project.

## General

- [x] review use of crispy forms, consider removing it from some apps
- [x] complete remove crispy forms from the project and update all documentation
- [x] add simplenotes app
- [x] brainstorm the best strategy to implement photos/photos series/video clips
- [x] add outpatientprescriptions app
- [x] implement internal ward/bed transfer management system
- [] add examsresults app
- [] add examsrequests app
- [] add dischargereports app
- [] add reports app

## SampleContent

- [x] create sample_content app

## Dailynotes

- [x] add insert sample content button to create template Ok
- [x] review details template layout on mobile
- [x] fix back button ('Voltar') on dailynote duplicate page (it returns to dailynote details). I think it should always return to the patient timeline Ok
- [x] cleanup dailynotes app templates

## HisptoryAndPhysicals

- [x] cleanup historyandphysicals app templates the same way as dailynotes app
- [x] remove crispy forms from historyandphysicals app

## Patients

- [x] update adding hospital records from edit patient form
- [x] cleanup patients app templates
- [x] remove crispy forms from patients app
- [x] implement internal ward/bed transfer system
- [x] consolidate medical actions on patient details page
- [x] separate personal data editing from medical status changes

## Mediafiles

- [] incorporate filepond assets into the project static files
- [] fix photos and photoseries caption text field styling
- [] evaluate mediafiles event cards for UI/UX
- [] evaluate create, edit, and details templates UI/UX visual polution

## OutpatientPrescriptions

- [] fix single drug card UI/UX
- [] fix list of drugs ordering, consider using drag and drop for reordering
- [] improve new item button visibility

## Observations

- try to use
  `Always use the actual code/codebase as your source of truth. Do not rely on your progress docs efforts. Your docs are pointers to what you've done, not reliable memories.`

## Improve nginx static files serving

change install-minimal.sh to copy files to a prefixed path accessible to ngnix in /var/www/

Option 1: Use a Bind Mount Instead of Volume

Modify your docker-compose.yml to use a bind mount to a directory nginx can access:

volumes: - /var/www/eqmd/static:/app/staticfiles

Then in nginx.conf:
location /static/ {
alias /var/www/eqmd/static/; # ... rest of config
}

2. Modify docker-compose.yml

Change the static files volume from:
volumes: - eqmd_static_files:/app/staticfiles

To a bind mount:
volumes: - /var/www/eqmd/static:/app/staticfiles

3. Update nginx.conf

location /static/ {
alias /var/www/eqmd/static/;
expires 1y;
add_header Cache-Control "public, immutable";
}
Option 3: Copy Files to nginx-accessible Directory

Add a step to copy static files to /var/www/:

# After collectstatic, copy to nginx directory

sudo mkdir -p /var/www/eqmd/static
sudo cp -r /var/lib/docker/volumes/eqmd_static_files/\_data/\* /var/www/eqmd/static/
sudo chown -R www-data:www-data /var/www/eqmd/static/
