from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe


register = template.Library()


STATICFILES = {
    'chosen': [
        'chosen/1.8.7/chosen.jquery.min.js',
        'chosen/1.8.7/chosen.min.css',
    ],
}


def get_static(file_type):
    static_names = []
    for filelist in STATICFILES.values():
        for filename in filelist:
            if filename.endswith(file_type):
                static_names.append(static(filename))
    return static_names


@register.simple_tag(name='oscar_pg_search_static_js')
def static_js():
    return mark_safe('\n'.join([f'<script src="{file}"></script>'
                      for file in get_static('js')]))


@register.simple_tag(name='oscar_pg_search_static_css')
def static_css():
    return mark_safe('\n'.join([f'<link rel="stylesheet" href="{file}" />'
                      for file in get_static('css')]))


@register.simple_tag(name='oscar_pg_search_static_all')
def static_all():
    return mark_safe(f'{static_js()}\n{static_css()}')


@register.simple_tag(name='oscar_pg_search_base')
def base():
    chosen_script = """
    <script>
        $(".chosen-select").chosen();
        $(".chosen-select").change(function (){
            this.form.submit();
        });
    </script>
    """
    return mark_safe(f'{static_all()}\n{chosen_script}')