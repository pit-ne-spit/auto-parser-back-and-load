# Инструкция по удалению и установке PostgreSQL

## Текущая версия
- PostgreSQL 15 установлен в `C:\Program Files\PostgreSQL\15\`

## Удаление PostgreSQL 15

### Способ 1: Через Панель управления (рекомендуется)
1. Откройте **Панель управления** → **Программы и компоненты**
2. Найдите **PostgreSQL 15**
3. Нажмите **Удалить**
4. Следуйте инструкциям мастера удаления

### Способ 2: Через PowerShell (от имени администратора)
```powershell
# Остановить службы PostgreSQL
Stop-Service -Name "postgresql*" -Force

# Найти и удалить через установщик
$uninstaller = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | 
    Where-Object {$_.DisplayName -like "*PostgreSQL 15*"} | 
    Select-Object -ExpandProperty UninstallString

if ($uninstaller) {
    & $uninstaller /S
}
```

### Способ 3: Ручное удаление (если стандартное не работает)
1. Остановите службы PostgreSQL через **Службы** (services.msc)
2. Удалите директорию `C:\Program Files\PostgreSQL\15\`
3. Удалите данные (если нужно сохранить - сделайте бэкап):
   - `C:\ProgramData\PostgreSQL\15\`
   - `%APPDATA%\postgresql\`
4. Очистите переменные окружения PATH от ссылок на PostgreSQL

## Установка PostgreSQL 18.1

### Скачать установщик
1. Перейдите на: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Выберите **PostgreSQL 18.1** для Windows x86-64
3. Скачайте **Windows x86-64** installer

### Установка
1. Запустите установщик от имени администратора
2. Выберите компоненты:
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (опционально, но полезно)
   - ✅ Stack Builder (опционально)
   - ✅ Command Line Tools (обязательно!)
3. Укажите директорию установки: `C:\Program Files\PostgreSQL\18`
4. Укажите директорию данных: `C:\ProgramData\PostgreSQL\18\data`
5. **ВАЖНО:** Запомните пароль для пользователя `postgres`!
6. Порт: оставьте `5432` (по умолчанию)
7. Локаль: выберите `Russian, Russia` или `English, United States`
8. Завершите установку

### После установки
1. Проверьте, что служба PostgreSQL запущена
2. Проверьте подключение:
   ```bash
   psql -U postgres -c "SELECT version();"
   ```

## Настройка для проекта

После установки обновите `.env` файл:
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=ваш_пароль_от_postgres
DB_NAME=che168_db
```
