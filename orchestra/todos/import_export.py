import csv

from django.conf import settings
from django.utils import timezone
from tempfile import NamedTemporaryFile

from orchestra.google_apps.permissions import write_with_link_permission
from orchestra.google_apps.service import Service


def _write_template_rows(writer, todo, depth):
    writer.writerow(
        [todo['remove_if'], todo['skip_if']] +
        ([''] * depth) +
        [todo['description']])
    for child in reversed(todo.get('items', [])):
        _write_template_rows(writer, child, depth + 1)


def export_to_spreadsheet(todo_list_template):
    with NamedTemporaryFile(mode='w+', delete=False) as file:
        writer = csv.writer(file)
        writer.writerow(['Remove if', 'Skip if'])
        _write_template_rows(writer, todo_list_template.todos, 0)
        file.flush()
        service = Service(settings.GOOGLE_P12_PATH,
                          settings.GOOGLE_SERVICE_EMAIL)
        sheet = service.insert_file(
            '{} - {}'.format(todo_list_template.description, timezone.now()),
            '',
            settings.ORCHESTRA_TODO_LIST_TEMPLATE_EXPORT_GDRIVE_FOLDER,
            'text/csv',
            'application/vnd.google-apps.spreadsheet',
            file.name
        )
        service.add_permission(sheet['id'], write_with_link_permission)
        return 'https://docs.google.com/spreadsheets/d/{}'.format(sheet['id'])


def import_from_spreadsheet(todo_list_template, spreadsheet_url):
    pass
