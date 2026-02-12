"""Тестовый скрипт для проверки перевода с китайского на русский."""

import json
import sys
from pathlib import Path

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.translator import translate_dict, translate_text


def main():
    """Тестирование перевода."""
    example_file = Path(__file__).parent.parent / "example.txt"
    
    print("Загрузка данных из example.txt...")
    with open(example_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Берем первый автомобиль
    first_car = data['result'][0]
    
    print("\n" + "=" * 80)
    print("ПРИМЕРЫ ПЕРЕВОДА:")
    print("=" * 80)
    
    # Примеры отдельных переводов
    test_texts = [
        "胎压监测装置",
        "基本参数",
        "发动机",
        "变速箱类型",
        "分期购车",
        "以旧换新",
        "汽油",
        "涡轮增压",
        "三厢车",
    ]
    
    print("\n1. Перевод отдельных терминов:")
    print("-" * 80)
    for text in test_texts:
        translated = translate_text(text)
        print(f"  {text:30} -> {translated}")
    
    # Примеры из данных автомобиля
    print("\n2. Перевод полей из данных автомобиля:")
    print("-" * 80)
    
    car_data = first_car.get('data', {})
    
    # Проверяем некоторые поля
    if 'engine_type' in car_data:
        print(f"  engine_type: {car_data['engine_type']}")
        print(f"              -> {translate_text(car_data['engine_type'])}")
    
    if 'transmission_type' in car_data:
        print(f"  transmission_type: {car_data['transmission_type']}")
        print(f"                   -> {translate_text(car_data['transmission_type'])}")
    
    if 'body_type' in car_data:
        print(f"  body_type: {car_data['body_type']}")
        print(f"          -> {translate_text(car_data['body_type'])}")
    
    # Проверяем конфигурацию
    if 'configuration' in car_data:
        config = car_data['configuration']
        if 'paramtypeitems' in config:
            print("\n3. Перевод названий групп параметров:")
            print("-" * 80)
            for param_type in config['paramtypeitems'][:3]:  # Первые 3 группы
                name = param_type.get('name', '')
                translated = translate_text(name)
                print(f"  {name:30} -> {translated}")
                
                # Показываем несколько параметров из первой группы
                if param_type.get('paramitems'):
                    print(f"    Параметры:")
                    for param in param_type['paramitems'][:3]:  # Первые 3 параметра
                        param_name = param.get('name', '')
                        param_value = param.get('value', '')
                        param_name_tr = translate_text(param_name)
                        param_value_tr = translate_text(param_value)
                        print(f"      {param_name:40} -> {param_name_tr}")
                        if param_value != param_value_tr:
                            print(f"        Значение: {param_value:40} -> {param_value_tr}")
    
    # Полный перевод первого автомобиля
    print("\n4. Полный перевод первого автомобиля:")
    print("-" * 80)
    print("Перевод выполняется...")
    
    translated_car = translate_dict(first_car)
    
    # Сохраняем результат
    output_file = Path(__file__).parent.parent / "translated_car_ru.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_car, f, indent=2, ensure_ascii=False)
    
    print(f"Результат сохранен в: {output_file}")
    
    # Показываем несколько примеров переведенных полей
    print("\n5. Примеры переведенных полей:")
    print("-" * 80)
    
    if 'data' in translated_car:
        data = translated_car['data']
        
        # Проверяем extra.option
        if 'extra' in data and 'option' in data['extra']:
            option = data['extra']['option']
            if 'displayopts' in option:
                print("\n  Опции (displayopts):")
                for opt in option['displayopts'][:3]:
                    print(f"    {opt.get('optionname', '')}")
            
            if 'moreoptions' in option:
                print("\n  Дополнительные опции (moreoptions):")
                for group in option['moreoptions'][:2]:
                    group_name = group.get('groupname', '')
                    print(f"    Группа: {group_name}")
                    if 'opts' in group:
                        for opt in group['opts'][:2]:
                            print(f"      - {opt.get('optionname', '')}")
        
        # Проверяем configuration
        if 'configuration' in data:
            config = data['configuration']
            if 'paramtypeitems' in config:
                print("\n  Группы параметров конфигурации:")
                for param_type in config['paramtypeitems']:
                    name = param_type.get('name', '')
                    print(f"    - {name}")
    
    print("\n" + "=" * 80)
    print("Тестирование завершено!")
    print("=" * 80)


if __name__ == "__main__":
    main()
