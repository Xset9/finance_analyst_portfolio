import pandas as pd
import glob
import os

# ============================================================
# НАСТРОЙКИ (обязательно отредактируйте под свою структуру)
# ============================================================
input_folder = r'C:\Users\ВашеИмя\Documents\Продажи'           # папка с исходными файлами
output_file = r'C:\Users\ВашеИмя\Documents\итог_плоский.xlsx'  # куда сохранить результат
price_file = r'C:\Users\ВашеИмя\Documents\цены.xlsx'           # файл с ценами (должен содержать колонки: Артикул, код, месяц, цена)

# Имена колонок в исходных файлах (уточните по своим данным)
id_columns = ['Контрагент', 'код', 'Бренд', 'Характеристика', 'Артикул', 'Статус SKU']
type_column = 'Вид прод.'           # колонка, где указано 'Промо продажи' / 'Рег продажи'
months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
          'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']   # названия месяцев

# Суффиксы для колонок количества и скидок (если колонки называются, например, 'янв' и 'янв_скидка')
suffix_qty = ''          # пусто, если колонки количества называются просто 'янв'
suffix_disc = '_скидка'  # добавляется к названию месяца для колонки скидки

# Если в ваших файлах колонки скидок называются иначе, измените suffix_disc.
# Если колонки количества и скидок уже в отдельных строках (а не в колонках), логика будет другой.
# ============================================================

def process_file(filepath):
    """Обрабатывает один файл, возвращает датафрейм в длинном формате (одна строка на месяц) с количеством и скидкой"""
    df = pd.read_excel(filepath)

    # Оставляем только активные SKU
    if 'Статус SKU' in df.columns:
        df = df[df['Статус SKU'] == 'Активный'].copy()

    # Собираем списки колонок для месяцев
    qty_columns = [f'{m}{suffix_qty}' for m in months]
    disc_columns = [f'{m}{suffix_disc}' for m in months]

    # Проверяем, что все нужные колонки есть в файле
    for col in qty_columns + disc_columns:
        if col not in df.columns:
            print(f'В файле {filepath} отсутствует колонка {col}. Пропускаем файл.')
            return pd.DataFrame()

    # Выбираем только нужные колонки
    all_cols = id_columns + [type_column] + qty_columns + disc_columns
    df = df[all_cols]

    # Преобразуем из широкого формата в длинный (unpivot)
    df_qty = pd.melt(df, id_vars=id_columns + [type_column], value_vars=qty_columns,
                     var_name='месяц', value_name='количество')
    df_disc = pd.melt(df, id_vars=id_columns + [type_column], value_vars=disc_columns,
                      var_name='месяц', value_name='скидка')

    # Убираем суффиксы, чтобы названия месяцев совпадали
    df_qty['месяц'] = df_qty['месяц'].str.replace(suffix_qty, '', regex=False)
    df_disc['месяц'] = df_disc['месяц'].str.replace(suffix_disc, '', regex=False)

    # Объединяем количество и скидку
    df_long = pd.merge(df_qty, df_disc, on=id_columns + [type_column, 'месяц'], how='outer')
    df_long['количество'] = pd.to_numeric(df_long['количество'], errors='coerce').fillna(0)
    df_long['скидка'] = pd.to_numeric(df_long['скидка'], errors='coerce').fillna(0)

    return df_long

def main():
    files = glob.glob(os.path.join(input_folder, '*.xlsx'))
    if not files:
        print(f'Файлы не найдены в папке {input_folder}')
        return

    all_data = []
    for file in files:
        print(f'Обрабатывается: {file}')
        df_part = process_file(file)
        if not df_part.empty:
            all_data.append(df_part)

    if not all_data:
        print('Нет данных для обработки.')
        return

    combined = pd.concat(all_data, ignore_index=True)

    # Загружаем цены
    try:
        prices = pd.read_excel(price_file)
        # Предположим, что в price_file есть колонки: 'Артикул', 'код', 'месяц', 'цена'
        # Если названия отличаются, переименуйте их
        prices = prices[['Артикул', 'код', 'месяц', 'цена']]
        prices['цена'] = pd.to_numeric(prices['цена'], errors='coerce')
    except Exception as e:
        print(f'Ошибка при чтении файла цен: {e}')
        return

    # Присоединяем цены
    combined = combined.merge(prices, on=['Артикул', 'код', 'месяц'], how='left')
    combined['цена'].fillna(0, inplace=True)

    # Теперь разворачиваем по типу продаж: из длинного формата (промо/регуляр) в широкий
    # Для количества
    pivot_qty = combined.pivot_table(index=id_columns + ['месяц'], columns=type_column,
                                     values='количество', aggfunc='first').reset_index()
    # Для скидки
    pivot_disc = combined.pivot_table(index=id_columns + ['месяц'], columns=type_column,
                                      values='скидка', aggfunc='first').reset_index()

    # Объединяем
    result = pd.merge(pivot_qty, pivot_disc, on=id_columns + ['месяц'], suffixes=('_кол', '_скидка'))

    # Переименовываем колонки для удобства
    rename_map = {
        'Промо продажи_кол': 'количество_промо',
        'Рег продажи_кол': 'количество_регуляр',
        'Промо продажи_скидка': 'скидка_промо',
        'Рег продажи_скидка': 'скидка_регуляр'
    }
    result.rename(columns=rename_map, inplace=True)

    # Добавляем цену (цена не зависит от типа продаж, берём из любой строки)
    price_cols = id_columns + ['месяц', 'цена']
    price_unique = combined[price_cols].drop_duplicates()
    result = result.merge(price_unique, on=id_columns + ['месяц'], how='left')

    # Расчёт выручки
    result['выручка_промо'] = result['количество_промо'] * result['цена'] * (1 - result['скидка_промо'])
    result['выручка_регуляр'] = result['количество_регуляр'] * result['цена'] * (1 - result['скидка_регуляр'])

    # Финальный набор колонок
    final_columns = id_columns + ['месяц', 'количество_промо', 'количество_регуляр',
                                  'выручка_промо', 'выручка_регуляр']
    result = result[final_columns]

    # Сохраняем результат
    result.to_excel(output_file, index=False)
    print(f'Готово! Результат сохранён в {output_file}')

if __name__ == '__main__':
    main()