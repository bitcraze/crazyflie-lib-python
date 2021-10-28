## Define mini-templates for each portion of the doco.

<%!
    def title(heading, name):
        return name.split('.')[-1]
%>

<%!
    def page_id(name):
        return name.replace('.', '-')
%>

<%!
    from pathlib import Path
    def linkify(name, module, base_module):
        link = module.url(relative_to=base_module).replace('html', 'md')
        # we do not support hashes in uri right now
        index = link.find('#')
        if index > 0:
            link = link[:index]

        # we do not support linkin to builtins
        index = link.find('.ext')
        if index > 0:
            return name

        return f'[{name}]({link})'
%>

<%!
    import re
    def deflist(s):
        param_re = r':param (.*):|@param (\w+)'
        params_found = False
        in_param = False
        desc = str()

        #
        # Here we try to turn the docstring parameters into a markdown table
        #
        # :param param1: description1
        # :param param2: desccription2
        #                description2 continues
        # :param param3:
        #
        # into:
        #
        # #### Parameters
        #
        # | Name   | Description |
        # | ----   | ----------- |
        # | param1 | decription1 |
        # | param2 | description2 description2 continues |
        # | param3 | |
        #
        out = str()
        for line in s.splitlines():
            match = re.match(param_re, line)
            if match is not None:
                if not params_found:
                    params_found = True
                    out += h(4, 'Parameters') + '\n'
                    out += '\n' + '| Name | Description |' + '\n'
                    out +=        '| ---- | ----------- |' + '\n'

                if in_param:
                    out += f'{desc} |' + '\n'

                in_param = True

                if match.group(1) is not None:
                    out += f'| {match.group(1)} | '
                else:
                    out += f'| {match.group(2)} | '

                desc = line.replace(match.group(0), '')

            elif in_param:
                desc += line
            else:
                out += line + '\n'

        if in_param:
            out += f'{desc} |' + '\n'

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
