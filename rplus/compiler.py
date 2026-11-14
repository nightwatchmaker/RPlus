"""Small C11 backend for the numeric R+ subset."""

from .ast import (
    Assignment, Binary, Block, Call, ExpressionStatement, FunctionDeclaration,
    ForStatement, WhileStatement, BreakStatement, ContinueStatement, GetExpression, IndexExpression, IfStatement, ListLiteral, Literal, Program, ReturnStatement, Unary,
    StructDeclaration, StructLiteral,
    ImplDeclaration,
    SetExpression, SetIndexStatement,
    Variable,
    VariableDeclaration,
)


class CompileError(Exception):
    pass


class CCompiler:
    def __init__(self):
        self.types = {}
        self.function_return_types = {}
        self.list_lengths = {}
        self.list_names = set()
        self.structs = {}
        self.methods = {}

    def compile(self, program: Program):
        self.types = {}
        self.list_lengths = {}
        self.list_names = set()
        self.structs = {
            statement.name: dict(statement.fields)
            for statement in program.statements
            if isinstance(statement, StructDeclaration)
        }
        self.methods = {
            (statement.target, method.name): method
            for statement in program.statements
            if isinstance(statement, ImplDeclaration)
            for method in statement.methods
        }
        self.function_return_types = {
            statement.name: statement.return_type or "Any"
            for statement in program.statements
            if isinstance(statement, FunctionDeclaration)
        }
        functions = [statement for statement in program.statements if isinstance(statement, FunctionDeclaration)]
        methods = [
            (statement.target, method)
            for statement in program.statements if isinstance(statement, ImplDeclaration)
            for method in statement.methods
        ]
        top_level = [statement for statement in program.statements if not isinstance(statement, (FunctionDeclaration, StructDeclaration, ImplDeclaration))]
        lines = [
            "#include <stdio.h>",
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdlib.h>",
            "#include <string.h>",
            "#include <time.h>",
            "",
            "typedef struct { int *data; size_t len; } RListInt;",
            "typedef struct { double *data; size_t len; } RListFloat;",
            "typedef struct { const char **data; size_t len; } RListString;",
            "RListInt rplus_list_int(const int *source, size_t len) {",
            "    RListInt result = { malloc(len * sizeof(int)), len };",
            "    if (!result.data) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
            "    for (size_t i = 0; i < len; i++) result.data[i] = source[i];",
            "    return result;",
            "}",
            "RListFloat rplus_list_float(const double *source, size_t len) {",
            "    RListFloat result = { malloc(len * sizeof(double)), len };",
            "    if (!result.data) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
            "    for (size_t i = 0; i < len; i++) result.data[i] = source[i];",
            "    return result;",
            "}",
            "RListString rplus_list_string(const char *const *source, size_t len) {",
            "    RListString result = { malloc(len * sizeof(const char *)), len };",
            "    if (!result.data) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
            "    for (size_t i = 0; i < len; i++) result.data[i] = source[i];",
            "    return result;",
            "}",
            "",
            "char *rplus_randomize(const char *source) {",
            "    size_t len = strlen(source);",
            "    char *result = malloc(len + 1);",
            "    if (!result) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
            "    memcpy(result, source, len + 1);",
            "    static bool seeded = false;",
            "    if (!seeded) { srand((unsigned)time(NULL)); seeded = true; }",
            "    for (size_t i = len; i > 1; i--) {",
            "        size_t j = (size_t)rand() % i;",
            "        char swap = result[i - 1]; result[i - 1] = result[j]; result[j] = swap;",
            "    }",
            "    return result;",
            "}",
            "",
            "char *rplus_input(const char *prompt) {",
            "    fputs(prompt, stdout); fflush(stdout);",
            "    char *result = malloc(4096);",
            "    if (!result) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
            "    if (!fgets(result, 4096, stdin)) result[0] = '\\0';",
            "    result[strcspn(result, \"\\r\\n\")] = '\\0';",
            "    return result;",
            "}",
            "",
        ]
        for name, fields in self.structs.items():
            lines.append(f"typedef struct {{")
            for field_name, field_type in fields.items():
                lines.append(f"    {self.c_type(field_type)} {field_name};")
            lines.extend([f"}} {name};", ""])
            lines.extend([
                f"typedef struct {{ {name} *data; size_t len; }} RList{name};",
                f"RList{name} rplus_list_{name}(const {name} *source, size_t len) {{",
                f"    RList{name} result = {{ malloc(len * sizeof({name})), len }};",
                "    if (!result.data) { fprintf(stderr, \"R+ out of memory\\n\"); exit(1); }",
                f"    for (size_t i = 0; i < len; i++) result.data[i] = source[i];",
                "    return result;",
                "}",
                "",
            ])
        for function in functions:
            lines.extend(self.compile_function(function))
            lines.append("")
        for target, method in methods:
            lines.extend(self.compile_function(method, target))
            lines.append("")
        lines.extend(["int main(void) {", *self.compile_statements(top_level, 1)])
        for name in sorted(self.list_names):
            lines.append(f"    free({name}.data);")
        lines.extend(["    return 0;", "}"])
        return "\n".join(lines) + "\n"

    def compile_function(self, function, method_target=None):
        previous_types = self.types
        self.types = {name: type_name or "Any" for name, type_name in function.parameters}
        return_type = self.c_type(function.return_type or "Any")
        function_name = f"{method_target}_{function.name}" if method_target else function.name
        parameters = []
        for index, (name, type_name) in enumerate(function.parameters):
            if method_target and index == 0 and type_name == f"&mut {method_target}":
                parameters.append(f"{method_target} *{name}")
            elif method_target and index == 0 and type_name == f"&{method_target}":
                parameters.append(f"const {method_target} *{name}")
            else:
                parameters.append(f"{self.c_type(type_name or 'Any')} {name}")
        parameters = ", ".join(parameters)
        lines = [f"{return_type} {function_name}({parameters}) {{"]
        lines.extend(self.compile_statements(function.body.statements, 1))
        if return_type == "void":
            lines.append("    return;")
        lines.append("}")
        self.types = previous_types
        return lines

    def compile_statements(self, statements, level):
        lines = []
        indent = "    " * level
        for statement in statements:
            if isinstance(statement, VariableDeclaration):
                type_name = statement.type_name or self.infer_expression_type(statement.initializer)
                self.types[statement.name] = type_name
                if type_name.startswith("List[") and isinstance(statement.initializer, ListLiteral):
                    self.list_lengths[statement.name] = len(statement.initializer.elements)
                    self.list_names.add(statement.name)
                    element_type = type_name[5:-1]
                    supported = ("Int", "Float", "String")
                    if element_type not in supported and element_type not in self.structs:
                        raise CompileError("Native dynamic lists need a supported element type")
                    if element_type in supported:
                        helper = {"Int": "rplus_list_int", "Float": "rplus_list_float", "String": "rplus_list_string"}[element_type]
                        c_element = {"Int": "int", "Float": "double", "String": "const char*"}[element_type]
                    else:
                        helper = f"rplus_list_{element_type}"
                        c_element = element_type
                    values = self.expression(statement.initializer)
                    lines.append(f"{indent}{self.c_type(type_name)} {statement.name} = {helper}(({c_element}[]){values}, {len(statement.initializer.elements)});")
                else:
                    lines.append(f"{indent}{self.c_type(type_name)} {statement.name} = {self.expression(statement.initializer)};")
            elif isinstance(statement, Assignment):
                lines.append(f"{indent}{statement.name} = {self.expression(statement.value)};")
            elif isinstance(statement, SetIndexStatement):
                target = self.expression(statement.object)
                lines.append(f"{indent}{target}.data[{self.expression(statement.index)}] = {self.expression(statement.value)};")
            elif isinstance(statement, SetExpression):
                target = self.expression(statement.object)
                operator = "->" if isinstance(statement.object, Variable) and str(self.types.get(statement.object.name, "")).startswith("&mut ") else "."
                lines.append(f"{indent}{target}{operator}{statement.name} = {self.expression(statement.value)};")
            elif isinstance(statement, ExpressionStatement):
                lines.append(f"{indent}{self.expression_statement(statement.expression)}")
            elif isinstance(statement, ReturnStatement):
                if statement.value is None:
                    lines.append(f"{indent}return;")
                else:
                    lines.append(f"{indent}return {self.expression(statement.value)};")
            elif isinstance(statement, BreakStatement):
                lines.append(f"{indent}break;")
            elif isinstance(statement, ContinueStatement):
                lines.append(f"{indent}continue;")
            elif isinstance(statement, WhileStatement):
                lines.append(f"{indent}while ({self.expression(statement.condition)}) {{")
                lines.extend(self.compile_statements(statement.body.statements, level + 1))
                lines.append(f"{indent}}}")
            elif isinstance(statement, ForStatement):
                if not isinstance(statement.iterable, Variable) or statement.iterable.name not in self.list_lengths:
                    raise CompileError("Native for loops currently require a local list variable")
                list_name = statement.iterable.name
                element_type = self.types[list_name][5:-1]
                index_name = f"__rplus_i_{level}_{len(lines)}"
                self.types[statement.name] = element_type
                lines.append(f"{indent}for (size_t {index_name} = 0; {index_name} < {list_name}.len; {index_name}++) {{")
                lines.append(f"{indent}    {self.c_type(element_type)} {statement.name} = {list_name}.data[{index_name}];")
                lines.extend(self.compile_statements(statement.body.statements, level + 1))
                lines.append(f"{indent}}}")
            elif isinstance(statement, IfStatement):
                lines.append(f"{indent}if {self.expression(statement.condition)} {{")
                lines.extend(self.compile_statements(statement.then_branch.statements, level + 1))
                lines.append(f"{indent}}}")
            elif isinstance(statement, Block):
                lines.append(f"{indent}{{")
                lines.extend(self.compile_statements(statement.statements, level + 1))
                lines.append(f"{indent}}}")
            else:
                raise CompileError(f"Unsupported statement {type(statement).__name__}")
        return lines

    def expression_statement(self, expression):
        if isinstance(expression, Call) and isinstance(expression.callee, Variable) and expression.callee.name in ("println", "print"):
            if len(expression.arguments) != 1:
                raise CompileError(f"{expression.callee.name} expects one argument")
            suffix = "\\n" if expression.callee.name == "println" else ""
            argument = expression.arguments[0]
            if self.infer_expression_type(argument) == "String":
                return f'printf("%s{suffix}", {self.expression(argument)});'
            if self.infer_expression_type(argument) == "Float":
                return f'printf("%g{suffix}", {self.expression(argument)});'
            return f'printf("%lld{suffix}", (long long)({self.expression(argument)}));'
        return f"{self.expression(expression)};"

    def expression(self, expression):
        if isinstance(expression, Literal):
            if isinstance(expression.value, bool): return "true" if expression.value else "false"
            if isinstance(expression.value, str): return '"' + expression.value.replace('\\', '\\\\').replace('"', '\\"') + '"'
            return repr(expression.value)
        if isinstance(expression, StructLiteral):
            fields = ", ".join(f".{name} = {self.expression(value)}" for name, value in expression.fields)
            return f"({expression.type_name}){{ {fields} }}"
        if isinstance(expression, IndexExpression):
            if isinstance(expression.object, Variable):
                list_name = expression.object.name
                return f"{list_name}.data[{self.expression(expression.index)}]"
            raise CompileError("Native indexing currently requires a local list variable")
        if isinstance(expression, GetExpression):
            object_expression = self.expression(expression.object)
            if isinstance(expression.object, Variable) and str(self.types.get(expression.object.name, "")).startswith("&"):
                return f"{object_expression}->{expression.name}"
            return f"({object_expression}).{expression.name}"
        if isinstance(expression, Variable): return expression.name
        if isinstance(expression, Unary): return f"({expression.operator}{self.expression(expression.right)})"
        if isinstance(expression, Binary): return f"({self.expression(expression.left)} {expression.operator} {self.expression(expression.right)})"
        if isinstance(expression, ListLiteral): return "{" + ", ".join(self.expression(element) for element in expression.elements) + "}"
        if isinstance(expression, Call):
            if isinstance(expression.callee, Variable) and expression.callee.name == "randomize":
                return f"rplus_randomize({', '.join(self.expression(argument) for argument in expression.arguments)})"
            if isinstance(expression.callee, Variable) and expression.callee.name == "input":
                return f"rplus_input({', '.join(self.expression(argument) for argument in expression.arguments)})"
            if isinstance(expression.callee, Variable) and expression.callee.name == "len":
                argument = expression.arguments[0]
                if isinstance(argument, Variable) and str(self.types.get(argument.name, "")).startswith("List["):
                    return f"{argument.name}.len"
                return f"(int)strlen({self.expression(argument)})"
            if isinstance(expression.callee, GetExpression):
                target_type = self.infer_expression_type(expression.callee.object)
                target_type = target_type.removeprefix("&mut ").removeprefix("&")
                method = self.methods.get((target_type, expression.callee.name))
                if method:
                    receiver = self.expression(expression.callee.object)
                    first_type = method.parameters[0][1] if method.parameters else None
                    receiver_argument = f"&{receiver}" if first_type and first_type.startswith("&") else receiver
                    args = ", ".join([receiver_argument, *(self.expression(argument) for argument in expression.arguments)])
                    return f"{target_type}_{expression.callee.name}({args})"
            return f"{self.expression(expression.callee)}({', '.join(self.expression(argument) for argument in expression.arguments)})"
        raise CompileError(f"Unsupported expression {type(expression).__name__}")

    def infer_expression_type(self, expression):
        if isinstance(expression, Literal):
            if isinstance(expression.value, bool): return "Bool"
            if isinstance(expression.value, int): return "Int"
            if isinstance(expression.value, float): return "Float"
            if isinstance(expression.value, str): return "String"
        if isinstance(expression, Binary):
            if expression.operator in ("&&", "||"): return "Bool"
            if expression.operator == "+" and self.infer_expression_type(expression.left) == "String": return "String"
            return "Int"
        if isinstance(expression, ListLiteral):
            element_type = self.infer_expression_type(expression.elements[0]) if expression.elements else "Any"
            return f"List[{element_type}]"
        if isinstance(expression, StructLiteral):
            return expression.type_name
        if isinstance(expression, GetExpression):
            object_type = self.infer_expression_type(expression.object)
            return self.structs.get(object_type, {}).get(expression.name, "Any")
        if isinstance(expression, Variable):
            return self.types.get(expression.name, "Int")
        if isinstance(expression, Call):
            if isinstance(expression.callee, Variable):
                if expression.callee.name == "randomize": return "String"
                if expression.callee.name == "input": return "String"
                if expression.callee.name == "len": return "Int"
                return self.function_return_types.get(expression.callee.name, "Int")
            return "Int"
        return "Int"

    def c_type(self, type_name):
        if type_name in (None, "Unit"): return "void"
        if type_name == "Float": return "double"
        if type_name == "Bool": return "bool"
        if isinstance(type_name, str) and type_name.startswith("&mut ") and type_name[5:] in self.structs:
            return f"{type_name[5:]}*"
        if isinstance(type_name, str) and type_name.startswith("&") and type_name[1:] in self.structs:
            return f"const {type_name[1:]}*"
        if type_name == "String" or (isinstance(type_name, str) and type_name.startswith("&")): return "const char*"
        if type_name in self.structs: return type_name
        if isinstance(type_name, str) and type_name.startswith("List["):
            element_type = type_name[5:-1]
            return {"List[Int]": "RListInt", "List[Float]": "RListFloat", "List[String]": "RListString"}.get(type_name, f"RList{element_type}")
        return "int"
