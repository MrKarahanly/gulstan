## Ежедневный отчёт по наличию препаратов на i-teka (Астана)

В репозитории добавлен скрипт, который:
- берёт ваш список препаратов из `medicine_list.txt`;
- проверяет наличие на `i-teka.kz` по городу (по умолчанию `astana`);
- выгружает результат в Excel `reports/i_teka_astana_YYYY-MM-DD.xlsx`.

### Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/daily_it_eka_report.py --city astana
```

### Формат входного списка

Файл `medicine_list.txt` — по одной позиции на строку.

### Поля в Excel

- `Препарат`
- `Поисковый_запрос`
- `Найден`
- `Кол-во_аптек`
- `Цена_от`
- `Ссылка_поиска`
- `Статус`
- `Дата_проверки`

### Ежедневный запуск

Добавлен GitHub Actions workflow `.github/workflows/daily-report.yml`:
- запускается ежедневно по cron;
- можно запускать вручную (`workflow_dispatch`);
- готовый `.xlsx` выгружается как artifact.

### Примечание

Структура страниц i-teka может меняться, поэтому часть строк может иметь статус `needs_manual_check`.
