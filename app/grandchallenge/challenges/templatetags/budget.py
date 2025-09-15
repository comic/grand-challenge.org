from django import template

register = template.Library()


@register.simple_tag
def get_phase_indices_for_task(task_id_for_phases, task_id):
    return [
        idx for idx, val in enumerate(task_id_for_phases) if val == task_id
    ]
