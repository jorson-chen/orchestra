import csv
import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from tempfile import NamedTemporaryFile

from orchestra.core.errors import SpreadsheetImportError
from orchestra.google_apps.permissions import write_with_link_permission
from orchestra.google_apps.service import Service
from orchestra.google_apps.convenience import get_google_spreadsheet_as_csv
from orchestra.models import TodoListTemplateImportRecord


REMOVE_IF_HEADER = 'Remove if'
SKIP_IF_HEADER = 'Skip if'


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
        writer.writerow([REMOVE_IF_HEADER, SKIP_IF_HEADER])
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


def import_from_spreadsheet(todo_list_template, spreadsheet_url, request):
    reader = get_google_spreadsheet_as_csv(spreadsheet_url, reader=csv.reader)
    header = next(reader)
    if header[:2] != [REMOVE_IF_HEADER, SKIP_IF_HEADER]:
        raise SpreadsheetImportError('Unexpected header: {}'.format(header))
    parent_items = []
    todos = None
    for rowindex, row in enumerate(reader):
        item = {
            'id': rowindex,
            'remove_if': json.loads(row[0] or '[]'),
            'skip_if': json.loads(row[1] or '[]'),
            'items': []
        }
        nonempty_columns = [(columnindex, text)
                            for columnindex, text in enumerate(row[2:])
                            if text]
        if len(nonempty_columns) == 0:
            continue
        elif len(nonempty_columns) > 1:
            raise SpreadsheetImportError(
                'More than one text entry in row {}: {}'.format(
                    rowindex, row))

        nonempty_index = nonempty_columns[0][0]
        item['description'] = nonempty_columns[0][1]

        if todos is None:
            todos = item
        elif nonempty_index <= len(parent_items):
            parent_items = parent_items[:nonempty_index]
            parent_items[-1].insert(0, item)
        else:
            raise SpreadsheetImportError(
                'Row {} is not a child of a previous row: {}'.format(
                    rowindex, row))
        parent_items.append(item['items'])

    todo_list_template.todos = todos
    with transaction.atomic():
        todo_list_template.save()
        TodoListTemplateImportRecord.objects.create(
            import_url=spreadsheet_url,
            todo_list_template=todo_list_template,
            importer=request.user)
