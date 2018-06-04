# ~*~ coding: utf-8 ~*~
import os
import yaml
import importlib

import ansible

from common.utils import get_logger, get_object_or_none
from .models import AdHocTask, AdHocContent

logger = get_logger(__file__)


def get_task_by_id(task_id):
    return get_object_or_none(AdHocTask, id=task_id)


def update_or_create_adhoc_task(
        task_name, assets=None, actions=None, nodes=None,
        interval=None, crontab=None, is_periodic=False,
        pattern='all', options=None, run_as_admin=False,
        run_as=None, created_by=None, vars=None, comment='',
        become=None,
    ):

    if not assets and not nodes:
        raise ValueError("Must set assets and nodes")
    elif not actions:
        raise ValueError("Actions must be set")

    defaults = {
        'name': task_name,
        'interval': interval,
        'crontab': crontab,
        'is_periodic': is_periodic,
        'comment': comment,
        'created_by': created_by,
    }

    created = False
    task, _ = AdHocTask.objects.update_or_create(
        defaults=defaults, name=task_name,
    )

    content = task.latest_content
    new_content = AdHocContent(
        task=task, actions=actions, vars=vars, pattern=pattern,
        options=options, run_as_admin=run_as_admin,
        run_as=run_as, become=become, created_by=created_by
    )

    changed = False
    if not content or content != new_content:
        logger.debug("Adhoc changed")
        changed = True
    elif assets and set(assets) != set(content.assets.all()):
        logger.debug("Assets changed")
        changed = True
    elif nodes and set(nodes) != set(content.nodes.all()):
        logger.debug("Nodes changed")
        changed = True

    if changed:
        logger.debug("Task create new adhoc: {}".format(task_name))
        new_content.save()
        if assets:
            new_content.assets.set(assets)
        if nodes:
            new_content.nodes.set(nodes)
        task.latest_content = new_content
        created = True
    return task, created


def generate_ansible_module_index():
    modules = {}
    module_path = os.path.join(ansible.__path__[0], 'modules')
    for catalog in os.listdir(module_path):
        if not os.path.isdir(os.path.join(module_path, catalog)):
            continue
        modules[catalog] = {}
        catalog_path = os.path.join(module_path, catalog)
        for module_file in os.listdir(catalog_path):
            if module_file == '__init__.py' or not module_file.endswith('.py'):
                continue
            module_name = module_file.replace('.py', '', 1)
            module = importlib.import_module('ansible.modules.{}.{}'.format(catalog, module_name))
            document = yaml.load(getattr(module, 'DOCUMENTATION'))
            modules[catalog][module_name] = document
            del module_name
    return modules
