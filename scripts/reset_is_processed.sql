-- Сброс флага is_processed для всех записей в raw_data
-- Это позволит перенормализовать данные с обновленным словарем переводов

UPDATE raw_data
SET is_processed = false
WHERE is_processed = true;

-- Проверка результата
SELECT 
    COUNT(*) FILTER (WHERE is_processed = true) as processed_count,
    COUNT(*) FILTER (WHERE is_processed = false) as unprocessed_count,
    COUNT(*) as total_count
FROM raw_data;
