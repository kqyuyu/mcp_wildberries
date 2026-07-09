import yaml
import json
from pathlib import Path


def parse_wb_swagger(yaml_path):
    """
    Парсит YAML файл Wildberries и возвращает READONLY методы

    Args:
        yaml_path: путь к YAML файлу (например, "02-items.yaml")
    """

    # Проверяем, что файл существует
    if not Path(yaml_path).exists():
        print(f"❌ Файл не найден: {yaml_path}")
        return []

    with open(yaml_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    methods = []
    for path, path_item in spec.get("paths", {}).items():
        for http_method, operation in path_item.items():
            if http_method not in ["get", "post", "put", "delete", "patch"]:
                continue

            is_readonly = operation.get("x-readonly-method", False)
            if not is_readonly:
                continue

            methods.append({
                "path": path,
                "method": http_method.upper(),
                "operation_id": operation.get("operationId", ""),
                "summary": operation.get("summary", ""),
                "description": operation.get("description", ""),
                "tags": operation.get("tags", []),
                "parameters": operation.get("parameters", []),
            })

    return methods


# Использование
if __name__ == "__main__":
    # Теперь можно передать любой файл
    yaml_file = "02-items.yaml"  # или "data/02-items.yaml"
    methods = parse_wb_swagger(yaml_file)

    print(f"✅ Всего READONLY методов в {yaml_file}: {len(methods)}\n")

    for m in methods:
        print(f"{m['method']} {m['path']}")
        print(f"  ID: {m['operation_id']}")
        print(f"  {m['summary']}\n")

    # Сохранить в JSON
    with open("methods_items.json", "w", encoding="utf-8") as f:
        json.dump(methods, f, ensure_ascii=False, indent=2)
    print("✅ Сохранено в methods_items.json")