## Define mini-templates for each portion of the doco.

<%!
    def title(heading, name):
        if name == 'cflib':
            return 'The CFLib API reference'
        else:
            return heading + ' ' + name
%>

<%!
    def page_id(name):
        if name == 'cflib':
            return 'api_reference'
        else:
            return name.replace('.', '-')
%>

<%!
    from pathlib import Path
    def linkify(name, module, base_module):
        link = module.url(relative_to=base_module).replace('html', 'md')
        return f'[{name}]({link})'
%>

<%!
    def deflist(s):
        out = str()
        for line in s.splitlines():
            out += line + '\n'
        return out
%>

<%!
    def h(level, s):
        return '#' * level + ' ' + s
%>

<%def name="function(func)" buffered="True">
    <%
        returns = show_type_annotations and func.return_annotation() or ''
        if returns:
            returns = ' \N{non-breaking hyphen}> ' + returns
    %>
```python
def ${func.name}(${", ".join(func.params(annotate=show_type_annotations))})${returns}
```
${func.docstring | deflist}
---
</%def>

<%def name="variable(var)" buffered="True">
    <%
        annot = show_type_annotations and var.type_annotation() or ''
        if annot:
            annot = ': ' + annot
    %>
```python
${var.name}${annot}
```
${var.docstring | deflist}
---
</%def>

<%def name="class_(cls)" buffered="True">
${h(4, cls.name)}
```python
${cls.name}(${", ".join(cls.params(annotate=show_type_annotations))})
```
${cls.docstring | deflist}
---

<%
  class_vars = cls.class_variables(show_inherited_members, sort=sort_identifiers)
  static_methods = cls.functions(show_inherited_members, sort=sort_identifiers)
  inst_vars = cls.instance_variables(show_inherited_members, sort=sort_identifiers)
  methods = cls.methods(show_inherited_members, sort=sort_identifiers)
  mro = cls.mro()
  subclasses = cls.subclasses()
%>
% if mro:
${h(3, 'Ancestors (in MRO)')}
    % for c in mro:
* ${linkify(c.refname, c, module)}
    % endfor

% endif
% if subclasses:
${h(3, 'Descendants')}
    % for c in subclasses:
* ${linkify(c.refname, c, module)}
    % endfor

% endif
% if class_vars:
${h(3, 'Class variables')}
    % for v in class_vars:
${variable(v)}

    % endfor
% endif
% if static_methods:
${h(3, 'Static methods')}
    % for f in static_methods:
${function(f)}

    % endfor
% endif
% if inst_vars:
${h(3, 'Instance variables')}
    % for v in inst_vars:
${variable(v)}

    % endfor
% endif
% if methods:
${h(3, 'Methods')}
    % for m in methods:
${function(m)}

    % endfor
% endif
</%def>

## Start the output logic for an entire module.

<%
  variables = module.variables(sort=sort_identifiers)
  classes = module.classes(sort=sort_identifiers)
  functions = module.functions(sort=sort_identifiers)
  submodules = module.submodules()
  heading = 'Namespace' if module.is_namespace else 'Module'
%>

---
title: ${title(heading, module.name)}
page_id: ${page_id(module.name)}
---
${deflist(module.docstring)}
---

% if submodules:
Sub-modules
-----------
    % for m in submodules:
* ${linkify(m.name, m, module)}
    % endfor
% endif

% if variables:
Variables
---------
    % for v in variables:
${variable(v)}

    % endfor
% endif

% if functions:
Functions
---------
    % for f in functions:
${function(f)}

    % endfor
% endif

% if classes:
Classes
-------
    % for c in classes:
${class_(c)}

    % endfor
% endif
