from django import template
from django.utils.html import escape
import difflib

register = template.Library()


@register.filter(name='diff_old_value')
def diff_old_value(old_value, new_value):
    """
    只在旧值上标记被删除的部分（红色）
    新值直接完整显示
    """
    if not old_value or not new_value:
        return escape(str(old_value or '-'))

    old_str = str(old_value)
    new_str = str(new_value)

    # 生成差异
    differ = difflib.SequenceMatcher(None, old_str, new_str)
    result = []
    for opcode in differ.get_opcodes():
        tag, i1, i2, j1, j2 = opcode
        if tag == 'equal':
            result.append(escape(old_str[i1:i2]))
        elif tag == 'delete':
            result.append(f'<span class="diff-removed">{escape(old_str[i1:i2])}</span>')
        elif tag == 'replace':
            result.append(f'<span class="diff-removed">{escape(old_str[i1:i2])}</span>')

    return ''.join(result) if result else escape(old_str)