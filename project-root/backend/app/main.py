import asyncio
import os
import shutil
import re
import json
import pandas as pd
from io import StringIO
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
import logging
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальное хранилище задач
current_tasks: Dict[str, Dict] = {}
task_results: Dict[str, Dict] = {}
HISTORY_FILE = "/app/data/processing_history.json"

# Создаем файл истории если его нет
history_dir = os.path.dirname(HISTORY_FILE)
os.makedirs(history_dir, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Запуск File Processor API...")

    # Создаем необходимые папки если их нет
    data_dir = "/app/data"
    tests_dir = os.path.join(data_dir, "Tests")
    results_dir = os.path.join(data_dir, "Results")

    os.makedirs(tests_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    logger.info(f"Директория данных: {data_dir}")
    logger.info(f"Директория тестов: {tests_dir}")
    logger.info(f"Директория результатов: {results_dir}")

    yield

    # Shutdown
    logger.info("Завершение работы...")
    save_history_to_file()


app = FastAPI(title="File Processor API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Модели данных
class PathRequest(BaseModel):
    path: str


class TaskResponse(BaseModel):
    task_id: str
    message: str
    timestamp: str


class LogMessage(BaseModel):
    message: str
    type: str = "info"
    timestamp: str = None


# Вспомогательные функции
def save_history_to_file():
    """Сохраняет историю обработки в файл"""
    try:
        # Собираем все завершенные задачи
        history_entries = []
        for task_id, task_info in current_tasks.items():
            if task_info.get("status") in ["completed", "failed"]:
                # Подготовка записи истории
                history_entry = {
                    "id": task_id,
                    "taskId": task_id,
                    "type": task_info.get("type"),
                    "status": task_info.get("status"),
                    "folderName": task_info.get("folder_name"),
                    "path": task_info.get("path"),
                    "startTime": task_info.get("started_at"),
                    "endTime": task_info.get("completed_at"),
                    "duration": None,
                    "error": task_info.get("error"),
                    "result": task_info.get("result"),
                    "logs": []
                }
                
                # Рассчитываем продолжительность
                if task_info.get("started_at") and task_info.get("completed_at"):
                    start = datetime.fromisoformat(task_info["started_at"])
                    end = datetime.fromisoformat(task_info["completed_at"])
                    duration_seconds = (end - start).seconds
                    if duration_seconds < 60:
                        history_entry["duration"] = f"{duration_seconds} сек"
                    else:
                        history_entry["duration"] = f"{duration_seconds // 60} мин {duration_seconds % 60} сек"
                
                # Сохраняем логи
                logs = task_info.get("logs", [])
                if logs:
                    history_entry["logs"] = [
                        {
                            "message": log.message if hasattr(log, 'message') else str(log),
                            "type": log.type if hasattr(log, 'type') else "info",
                            "timestamp": log.timestamp if hasattr(log, 'timestamp') else task_info.get("started_at")
                        }
                        for log in logs
                    ]
                
                history_entries.append(history_entry)
        
        # Сортируем по времени (новые сверху)
        history_entries.sort(key=lambda x: x.get("startTime", ""), reverse=True)
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_entries, f, ensure_ascii=False, indent=2)
        
        logger.info(f"История сохранена в файл: {HISTORY_FILE} ({len(history_entries)} записей)")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения истории: {e}")


def load_history_from_file():
    """Загружает историю обработки из файла"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                logger.info(f"Загружена история из файла: {len(history_data)} записей")
                return history_data
        else:
            logger.info("Файл истории не найден, будет создан новый")
            return []
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        return []


def save_to_history(task_data: Dict):
    """Сохраняет задачу в историю"""
    try:
        # Загружаем текущую историю
        history = load_history_from_file()
        
        # Создаем запись истории
        task_id = task_data.get("id") or task_data.get("task_id")
        history_entry = {
            "id": task_id or str(uuid.uuid4()),
            "taskId": task_id,
            "type": task_data.get("type"),
            "status": task_data.get("status"),
            "folderName": task_data.get("folder_name"),
            "path": task_data.get("path"),
            "startTime": task_data.get("started_at"),
            "endTime": task_data.get("completed_at"),
            "duration": None,
            "error": task_data.get("error"),
            "result": task_data.get("result"),
            "logs": []
        }
        
        # Рассчитываем продолжительность
        if task_data.get("started_at") and task_data.get("completed_at"):
            start = datetime.fromisoformat(task_data["started_at"])
            end = datetime.fromisoformat(task_data["completed_at"])
            duration_seconds = (end - start).seconds
            if duration_seconds < 60:
                history_entry["duration"] = f"{duration_seconds} сек"
            else:
                history_entry["duration"] = f"{duration_seconds // 60} мин {duration_seconds % 60} сек"
        
        # Сохраняем логи в правильном формате
        logs = task_data.get("logs", [])
        if logs:
            history_entry["logs"] = [
                {
                    "message": log.message if hasattr(log, 'message') else log.get("message", str(log)),
                    "type": log.type if hasattr(log, 'type') else log.get("type", "info"),
                    "timestamp": log.timestamp if hasattr(log, 'timestamp') else log.get("timestamp", task_data.get("started_at"))
                }
                for log in logs
            ]
        
        # Удаляем старую запись с тем же taskId если есть
        history = [h for h in history if h.get("taskId") != task_id]
        
        # Добавляем в начало истории (новые сверху)
        history.insert(0, history_entry)
        
        # Ограничиваем размер истории
        if len(history) > 100:
            history = history[:100]
        
        # Сохраняем в файл
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено в историю: {task_data.get('type')} - {task_data.get('folder_name')} ({len(logs)} логов)")
        
        return history_entry
        
    except Exception as e:
        logger.error(f"Ошибка сохранения в историю: {e}")
        return None


def add_log_to_task(task_id: str, message: str, type: str = "info"):
    """Добавляет лог в задачу"""
    if task_id not in current_tasks:
        current_tasks[task_id] = {"logs": [], "status": "running"}

    # Важно: сохраняем timestamp в правильном формате
    timestamp = datetime.now().isoformat()
    
    # Убедимся, что message - строка
    if not isinstance(message, str):
        message = str(message)
    
    # Форматируем сообщение
    formatted_message = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    
    # Создаем объект лога
    log_entry = LogMessage(
        message=formatted_message,
        type=type,
        timestamp=timestamp
    )
    
    # Ограничиваем количество логов (чтобы не перегружать память)
    if "logs" not in current_tasks[task_id]:
        current_tasks[task_id]["logs"] = []
    
    current_tasks[task_id]["logs"].append(log_entry)
    
    # Сохраняем только последние 1000 логов
    if len(current_tasks[task_id]["logs"]) > 1000:
        current_tasks[task_id]["logs"] = current_tasks[task_id]["logs"][-1000:]
    
    print(f"📝 Добавлен лог в задачу {task_id}: {type} - {message[:50]}...")
    return log_entry


def find_all_broken_files(root_path: str, task_id: str):
    """Находит ВСЕ битые .tst файлы без парных .txt во ВСЕХ вложенных папках"""
    add_log_to_task(task_id, "🔍 НАЧИНАЕМ РЕКУРСИВНЫЙ ПОИСК ВО ВСЕХ ПАПКАХ...", "info")
    add_log_to_task(task_id, "=" * 50, "info")
    add_log_to_task(task_id, f"📁 Корневая папка: {os.path.basename(root_path)}", "info")
    add_log_to_task(task_id, f"📁 Полный путь: {root_path}", "info")
    
    total_found = 0
    total_processed = 0
    moved_files = []
    
    # Считаем общее количество папок
    folder_count = 0
    for root, dirs, files in os.walk(root_path):
        folder_count += 1
    
    add_log_to_task(task_id, f"📊 Всего папок для проверки: {folder_count}", "info")
    
    current_folder = 0
    for folder, dirs, files in os.walk(root_path):
        current_folder += 1
        
        # Пропускаем папку "Изолированные_Битые"
        if "Изолированные_Битые" in folder:
            continue
            
        add_log_to_task(task_id, f"📂 Проверка папки [{current_folder}/{folder_count}]: {os.path.basename(folder)}", "info")
        add_log_to_task(task_id, f"   📍 Путь: {folder}", "info")

        # Ищем .tst файлы
        tst_files = [f for f in files if f.lower().endswith(".tst")]
        
        if not tst_files:
            add_log_to_task(task_id, "   ✅ .tst файлов не найдено", "info")
            continue
            
        add_log_to_task(task_id, f"   📄 Найдено .tst файлов: {len(tst_files)}", "info")
        
        folder_found = 0
        for tst in tst_files:
            total_processed += 1
            base = os.path.splitext(tst)[0]
            txt = base + ".txt"
            txt_path = os.path.join(folder, txt)

            if not os.path.exists(txt_path):
                # Найден битый файл!
                src = os.path.join(folder, tst)
                dest_dir = os.path.join(root_path, "Изолированные_Битые")
                os.makedirs(dest_dir, exist_ok=True)
                
                # Сохраняем структуру папок
                relative_path = os.path.relpath(folder, root_path)
                if relative_path != ".":
                    dest_dir = os.path.join(dest_dir, relative_path)
                    os.makedirs(dest_dir, exist_ok=True)
                
                dst = os.path.join(dest_dir, tst)

                try:
                    shutil.move(src, dst)
                    total_found += 1
                    folder_found += 1
                    moved_files.append({
                        "file": tst,
                        "from": folder,
                        "to": dest_dir,
                        "reason": f"Отсутствует {txt}"
                    })

                    add_log_to_task(task_id, "   ⚠️ БИТЫЙ ФАЙЛ НАЙДЕН ⚠️", "warning")
                    add_log_to_task(task_id, f"      Файл: {tst}", "info")
                    add_log_to_task(task_id, f"      Папка: {os.path.basename(folder)}", "info")
                    add_log_to_task(task_id, f"      Причина: отсутствует файл {txt}", "info")
                    add_log_to_task(task_id, f"      Перемещен в: {dest_dir}", "success")

                except Exception as e:
                    add_log_to_task(task_id, f"      ❌ Ошибка перемещения: {e}", "error")
            else:
                # Файл не битый
                add_log_to_task(task_id, f"   ✓ {tst} - OK (есть {txt})", "info")
                    
        if folder_found > 0:
            add_log_to_task(task_id, f"   📊 В папке найдено битых: {folder_found}", "success")
        else:
            add_log_to_task(task_id, f"   ✅ В папке битых файлов нет", "info")

    # Итоговый отчет
    add_log_to_task(task_id, "=" * 50, "info")
    if total_found > 0:
        add_log_to_task(task_id, f"🎉 ПОИСК ЗАВЕРШЕН! НАЙДЕНО: {total_found} БИТЫХ ФАЙЛОВ", "success")
    else:
        add_log_to_task(task_id, "✅ ПОИСК ЗАВЕРШЕН!", "success")
    
    add_log_to_task(task_id, f"📊 Обработано всего файлов: {total_processed}", "info")
    add_log_to_task(task_id, f"📊 Проверено папок: {current_folder}", "info")
    
    if total_found > 0:
        add_log_to_task(task_id, f"📁 Перемещено в: {os.path.join(root_path, 'Изолированные_Битые')}", "info")
    else:
        add_log_to_task(task_id, "📭 БИТЫХ ФАЙЛОВ НЕ НАЙДЕНО", "success")
    
    add_log_to_task(task_id, "=" * 50, "info")
    
    return {
        "found": total_found,
        "processed": total_processed,
        "folders_checked": current_folder,
        "moved_files": moved_files,
        "target_folder": os.path.join(root_path, "Изолированные_Битые") if total_found > 0 else None,
        "message": f"Найдено {total_found} битых файлов" if total_found > 0 else "Битых файлов не обнаружено"
    }


def parse_files_task(input_folder: str, task_id: str):
    """Парсит файлы в указанной папке с новой структурой"""
    add_log_to_task(task_id, f"🔍 Начинаем парсинг файлов в: {input_folder}", "info")

    # Создаем папку Results рядом с Tests
    data_dir = "/app/data"
    relative_path = os.path.relpath(input_folder, data_dir)
    output_folder = os.path.join(data_dir, "Results", relative_path)
    os.makedirs(output_folder, exist_ok=True)

    # Инициализация счетчика для отчета
    report_summary = {
        "Всего обработано": 0,
        "UCA файлы": 0,
        "Другое файлы": 0,
        "UCA - неполные/ошибки": 0,
        "Ошибки чтения": 0,
        "Распределение по категориям UCA": {}
    }

    # Функции парсинга
    def parse_summary_line(line):
        parts = [p.strip() for p in line.strip().split("\t") if p.strip()]
        if not parts:
            return None, None
        if len(parts) == 3 and parts[0] in ("Information", "Calculated Curve"):
            return parts[1], parts[2]
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
        return parts[0], ""

    def get_density_range(density_value):
        try:
            density_str = re.findall(r"(\d+)", str(density_value))[0]
            density = int(density_str)
        except Exception:
            return "Неизвестная_плотность"

        if 1100 <= density <= 1499:
            return "1100-1499"
        elif 1500 <= density <= 1899:
            return "1500-1899"
        elif 1900 <= density <= 2500:
            return "1900-2500"
        else:
            return f"Другая_{density}"

    def get_strength_type(value):
        val = str(value).lower()

        if "more than 14" in val:
            return "Алгоритм_больше_14"
        elif "less than 14" in val:
            return "Алгоритм_меньше_14"
        elif val.strip():
            cleaned_val = (
                val.strip()
                .replace('/', '_')
                .replace(':', '')
                .replace('<', 'меньше_')
                .replace('>', 'больше_')
                .replace('*', 'star')
                .replace('?', '')
            )
            return f"Алгоритм_{cleaned_val}"
        else:
            return "Неизвестный_алгоритм"

    def get_cement_class(value):
        if not value or pd.isna(value):
            return "Неизвестный_цемент"
        val = str(value).strip().replace("/", "_").replace(':', '').replace('<', 'меньше').replace('>', 'больше').replace('*', 'star').replace('?', '')
        return f"Цемент_{val}"

    def get_value(df, key_fragment):
        res = df[df["Параметр"].str.contains(key_fragment, case=False, na=False)]["Значение"]
        return res.iloc[0] if not res.empty else None

    # Основной цикл обработки
    try:
        # Получаем все .txt файлы рекурсивно
        txt_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith('.txt'):
                    txt_files.append((root, file))
                    
        add_log_to_task(task_id, f"📄 Найдено .txt файлов для обработки: {len(txt_files)}", "info")

        for root, file_name in txt_files:
            report_summary["Всего обработано"] += 1
            input_path = os.path.join(root, file_name)
            relative_root = os.path.relpath(root, input_folder)

            add_log_to_task(task_id, f"📄 Обрабатываем: {file_name}", "info")
            if relative_root != ".":
                add_log_to_task(task_id, f"   📁 Папка: {relative_root}", "info")

            try:
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except Exception as e:
                add_log_to_task(task_id, f"⚠️ Не удалось прочитать файл {file_name}: {e}", "error")
                report_summary["Ошибки чтения"] += 1
                continue

            # Поиск границ блоков
            summary_start, data_start = None, None
            for i, line in enumerate(lines):
                if "--Summary--" in line or "--Test Summary--" in line:
                    summary_start = i
                elif "--Data--" in line:
                    data_start = i
                    break

            # Определение типа файла
            is_uca_file = False
            summary_df = None

            if summary_start is not None and data_start is not None:
                summary_lines = lines[summary_start + 1:data_start]
                summary_data = []
                for line in summary_lines:
                    if not line.strip() or line.startswith("Full Path and File Name"):
                        continue
                    key, value = parse_summary_line(line)
                    if key:
                        summary_data.append((key, value))

                summary_df = pd.DataFrame(summary_data, columns=["Параметр", "Значение"])

                instrument_type = get_value(summary_df, "Instrument Type")

                if instrument_type and "uca" in str(instrument_type).lower():
                    is_uca_file = True
                    add_log_to_task(task_id, "➡️ Тип определен: UCA (по Instrument Type)", "success")

            # 2. Запасной вариант: проверка имени файла
            if not is_uca_file and "uca" in file_name.lower():
                is_uca_file = True
                add_log_to_task(task_id, "➡️ Тип определен: UCA (по имени файла)", "success")

            # --- ОБРАБОТКА UCA ---
            if is_uca_file:
                report_summary["UCA файлы"] += 1

                if summary_df is None:
                    add_log_to_task(task_id, f"⚠️ Пропуск: UCA-файл без блоков Summary/Data", "warning")
                    report_summary["UCA - неполные/ошибки"] += 1
                    continue

                density_val = get_value(summary_df, "Density")
                strength_val = get_value(summary_df, "Compressive Strength")
                cement_val = get_value(summary_df, "CementClass")

                missing_params = []
                if not density_val:
                    missing_params.append("Density")
                if not strength_val:
                    missing_params.append("Compressive Strength")
                if not cement_val:
                    missing_params.append("CementClass")

                # Основная папка UCA
                base_uca_folder = os.path.join(output_folder, "UCA")
                
                if not missing_params:
                    density_folder = get_density_range(density_val)
                    algorithm_folder = get_strength_type(strength_val)
                    cement_folder = get_cement_class(cement_val)
                    
                    # Сохраняем структуру папок
                    if relative_root != ".":
                        target_folder = os.path.join(base_uca_folder, relative_root, density_folder, algorithm_folder, cement_folder)
                    else:
                        target_folder = os.path.join(base_uca_folder, density_folder, algorithm_folder, cement_folder)
                        
                    category_key = f"{density_folder}/{algorithm_folder}/{cement_folder}"
                    add_log_to_task(task_id,
                                    f"✅ Категория: Плотность={density_folder}, Прочность={algorithm_folder}, Цемент={cement_folder}",
                                    "success")
                else:
                    target_folder = os.path.join(base_uca_folder, relative_root, "Неполные")
                    category_key = "Неполные"
                    report_summary["UCA - неполные/ошибки"] += 1
                    add_log_to_task(task_id, f"⚠️ Отправлен в Неполные: отсутствуют {', '.join(missing_params)}",
                                    "warning")

                if category_key not in report_summary["Распределение по категориям UCA"]:
                    report_summary["Распределение по категориям UCA"][category_key] = 0
                report_summary["Распределение по категориям UCA"][category_key] += 1

                os.makedirs(target_folder, exist_ok=True)

                # Data часть
                data_lines = lines[data_start + 1:] if data_start else []
                data_str = "".join(data_lines).replace(",", ".")

                try:
                    data_df = pd.read_csv(StringIO(data_str), sep="\t")
                except Exception as e:
                    add_log_to_task(task_id, f"⚠️ Ошибка чтения Data в {file_name}: {e}", "error")
                    if category_key != 'Неполные':
                        report_summary["UCA - неполные/ошибки"] += 1
                        if category_key in report_summary["Распределение по категориям UCA"]:
                            report_summary["Распределение по категориям UCA"][category_key] -= 1
                        report_summary["Распределение по категориям UCA"]["Неполные"] = report_summary[
                                                                                           "Распределение по категориям UCA"].get(
                            "Неполные", 0) + 1

                    target_folder = os.path.join(base_uca_folder, relative_root, "Неполные")
                    os.makedirs(target_folder, exist_ok=True)
                    data_df = None
                    category_key = "Неполные"

                # Сохранение
                base_name = os.path.splitext(file_name)[0]
                summary_path = os.path.join(target_folder, f"{base_name}_summary.xlsx")
                summary_df.to_excel(summary_path, index=False)

                if data_df is not None:
                    data_path = os.path.join(target_folder, f"{base_name}_data.xlsx")
                    data_df.to_excel(data_path, index=False)

                add_log_to_task(task_id, f"💾 Сохранено в {target_folder}", "success")

            # --- ОБРАБОТКА НЕ-UCA (Другое) ---
            else:
                report_summary["Другое файлы"] += 1
                add_log_to_task(task_id, "➡️ Тип определен: Другое", "info")

                rows = []
                for line in lines:
                    parts = [p.strip() for p in line.strip().split("\t") if p.strip()]
                    if parts:
                        rows.append(parts)

                if not rows:
                    add_log_to_task(task_id, f"⚠️ Файл {file_name} пуст", "warning")
                    report_summary["Ошибки чтения"] += 1
                    continue

                max_cols = max(len(r) for r in rows)
                col_names = [f"Колонка_{i + 1}" for i in range(max_cols)]
                df = pd.DataFrame([r + [''] * (max_cols - len(r)) for r in rows], columns=col_names)

                # Основная папка Другое
                base_other_folder = os.path.join(output_folder, "Другое")
                
                # Сохраняем структуру папок
                if relative_root != ".":
                    other_folder = os.path.join(base_other_folder, relative_root)
                else:
                    other_folder = base_other_folder
                    
                os.makedirs(other_folder, exist_ok=True)

                base_name = os.path.splitext(file_name)[0]
                excel_path = os.path.join(other_folder, f"{base_name}.xlsx")
                df.to_excel(excel_path, index=False)

                add_log_to_task(task_id, f"💾 Сохранено в {other_folder}", "success")

        # Итоговый отчет
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, "🎉 ИТОГОВЫЙ ОТЧЕТ", "success")
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, f"📁 Всего обработано: {report_summary['Всего обработано']}", "info")
        add_log_to_task(task_id, f"🔹 UCA-файлы: {report_summary['UCA файлы']}", "info")
        add_log_to_task(task_id, f"🔹 Другое: {report_summary['Другое файлы']}", "info")
        add_log_to_task(task_id, f"🔹 Неполные/Ошибки: {report_summary['UCA - неполные/ошибки']}", "info")
        add_log_to_task(task_id, f"🔹 Ошибки чтения: {report_summary['Ошибки чтения']}", "info")

        add_log_to_task(task_id, "\n📊 РАСПРЕДЕЛЕНИЕ UCA-ФАЙЛОВ:", "info")
        if report_summary["Распределение по категориям UCA"]:
            for category, count in report_summary["Распределение по категориям UCA"].items():
                add_log_to_task(task_id, f"  - {category}: {count} шт.", "info")
        else:
            add_log_to_task(task_id, "  (Нет категоризированных UCA-файлов)", "info")

        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, f"💾 Результаты сохранены в: {output_folder}", "success")
        add_log_to_task(task_id, "✅ Обработка завершена!", "success")

        return {
            "processed": report_summary["Всего обработано"],
            "output_folder": output_folder,
            "structure": {
                "UCA": base_uca_folder if 'base_uca_folder' in locals() else os.path.join(output_folder, "UCA"),
                "Другое": base_other_folder if 'base_other_folder' in locals() else os.path.join(output_folder, "Другое")
            },
            "summary": report_summary
        }

    except Exception as e:
        add_log_to_task(task_id, f"❌ Ошибка парсинга: {str(e)}", "error")
        return {"error": str(e), "processed": 0}


# ========== API ЭНДПОИНТЫ ==========

@app.get("/")
async def root():
    return {
        "message": "File Processor API",
        "статус": "работает",
        "русская_версия": "API обработки файлов",
        "endpoints": [
            "/api/find-broken-files (POST) - поиск битых .tst файлов",
            "/api/parse-files (POST) - парсинг файлов",
            "/api/folders (GET) - список папок в data",
            "/api/task/{task_id}/logs (GET) - получение логов",
            "/api/task/{task_id}/status (GET) - статус задачи",
            "/api/history (GET) - история обработки",
            "/docs - документация API"
        ]
    }


def get_folder_structure(base_path: str):
    """Рекурсивно получает структуру папок"""
    structure = []
    
    try:
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                # Считаем .txt файлы в папке и подпапках
                txt_count = 0
                for root, dirs, files in os.walk(item_path):
                    txt_count += len([f for f in files if f.lower().endswith('.txt')])
                
                folder_info = {
                    "name": item,
                    "path": item_path,
                    "files_count": txt_count,
                    "has_txt_files": txt_count > 0
                }
                
                # Получаем вложенные папки (только один уровень для простоты)
                subfolders = []
                try:
                    for sub_item in os.listdir(item_path):
                        sub_item_path = os.path.join(item_path, sub_item)
                        if os.path.isdir(sub_item_path):
                            sub_txt_count = 0
                            for root, dirs, files in os.walk(sub_item_path):
                                sub_txt_count += len([f for f in files if f.lower().endswith('.txt')])
                            
                            if sub_txt_count > 0:  # Показываем только папки с файлами
                                subfolders.append({
                                    "name": sub_item,
                                    "path": sub_item_path,
                                    "files_count": sub_txt_count,
                                    "has_txt_files": sub_txt_count > 0
                                })
                except PermissionError:
                    pass
                
                if subfolders:
                    folder_info["subfolders"] = sorted(subfolders, key=lambda x: x["name"])
                
                structure.append(folder_info)
                
    except PermissionError as e:
        logger.error(f"Permission error accessing {base_path}: {e}")
    except Exception as e:
        logger.error(f"Error scanning {base_path}: {e}")
    
    return sorted(structure, key=lambda x: x["name"])


@app.get("/api/folders")
async def get_folders():
    """Получает древовидную структуру папок в data директории"""
    data_dir = "/app/data"

    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    # Получаем основную структуру папок
    folders = get_folder_structure(data_dir)
    
    return {
        "data_directory": data_dir,
        "folders": folders
    }


@app.post("/api/find-broken-files", response_model=TaskResponse)
async def find_broken_files(request: PathRequest, background_tasks: BackgroundTasks):
    """Запускает поиск битых файлов в указанной папке - ДЛЯ ГЛАВНОЙ СТРАНИЦЫ"""
    try:
        task_id = str(uuid.uuid4())
        input_path = request.path

        # Проверяем существование папки
        if not os.path.exists(input_path):
            raise HTTPException(status_code=400, detail=f"Папка не существует: {input_path}")

        if not os.path.isdir(input_path):
            raise HTTPException(status_code=400, detail=f"Путь не является папкой: {input_path}")

        # Проверяем, что папка в data директории
        data_dir = "/app/data"
        if not input_path.startswith(data_dir):
            raise HTTPException(status_code=400, detail="Можно обрабатывать только папки внутри /app/data")

        # Создаем задачу
        current_tasks[task_id] = {
            "logs": [],
            "status": "running",
            "type": "find-broken",
            "path": input_path,
            "folder_name": os.path.basename(input_path),
            "started_at": datetime.now().isoformat(),
            "id": task_id
        }

        add_log_to_task(task_id, f"📁 Обрабатываем папку: {os.path.basename(input_path)}", "info")
        add_log_to_task(task_id, "⏳ Начинаем поиск битых файлов...", "info")

        # Сразу сохраняем в историю (начало задачи)
        save_to_history(current_tasks[task_id])

        # Запускаем фоновую задачу
        background_tasks.add_task(
            process_find_broken_task,
            task_id,
            input_path
        )

        return TaskResponse(
            task_id=task_id,
            message=f"Поиск битых файлов в '{os.path.basename(input_path)}' запущен",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Ошибка в find-broken-files: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска задачи: {str(e)}")


@app.post("/api/parse-files", response_model=TaskResponse)
async def parse_files_endpoint(request: PathRequest, background_tasks: BackgroundTasks):
    """Запускает парсинг файлов в указанной папке - ДЛЯ СТРАНИЦЫ ПАРСЕРА"""
    try:
        task_id = str(uuid.uuid4())
        input_path = request.path

        # Проверяем существование папки
        if not os.path.exists(input_path):
            raise HTTPException(status_code=400, detail=f"Папка не существует: {input_path}")

        if not os.path.isdir(input_path):
            raise HTTPException(status_code=400, detail=f"Путь не является папкой: {input_path}")

        # Проверяем, что папка в data директории
        data_dir = "/app/data"
        if not input_path.startswith(data_dir):
            raise HTTPException(status_code=400, detail="Можно обрабатывать только папки внутри /app/data")

        # Создаем задачу
        current_tasks[task_id] = {
            "logs": [],
            "status": "running",
            "type": "parse",
            "path": input_path,
            "folder_name": os.path.basename(input_path),
            "started_at": datetime.now().isoformat(),
            "id": task_id
        }

        add_log_to_task(task_id, f"📁 Обрабатываем папку: {os.path.basename(input_path)}", "info")
        add_log_to_task(task_id, "⏳ Начинаем парсинг...", "info")

        # Сразу сохраняем в историю (начало задачи)
        save_to_history(current_tasks[task_id])

        # Запускаем фоновую задачу
        background_tasks.add_task(
            process_parse_task,
            task_id,
            input_path
        )

        return TaskResponse(
            task_id=task_id,
            message=f"Парсинг файлов в '{os.path.basename(input_path)}' запущен",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"Ошибка в parse-files: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска задачи: {str(e)}")


# ========== ФОНОВЫЕ ЗАДАЧИ ==========

async def process_find_broken_task(task_id: str, input_path: str):
    """Фоновая задача поиска битых файлов"""
    try:
        add_log_to_task(task_id, "🔍 Начинаем поиск битых .tst файлов...", "info")
        add_log_to_task(task_id, f"📁 Папка: {os.path.basename(input_path)}", "info")
        
        # Запускаем обработку
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            find_all_broken_files,
            input_path,
            task_id
        )

        # Сохраняем результат
        task_results[task_id] = result
        
        # Обновляем статус задачи
        current_tasks[task_id]["status"] = "completed"
        current_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        current_tasks[task_id]["result"] = result
        
        add_log_to_task(task_id, "✅ Задача поиска завершена!", "success")
        
        # Сохраняем в историю
        save_to_history(current_tasks[task_id])
        
        print(f"✅ Задача {task_id} завершена. Сохранено в историю.")

    except Exception as e:
        logger.error(f"Ошибка в process_find_broken_task: {e}")
        add_log_to_task(task_id, f"❌ Критическая ошибка: {str(e)}", "error")
        current_tasks[task_id]["status"] = "failed"
        current_tasks[task_id]["error"] = str(e)
        current_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        # Сохраняем в историю даже при ошибке
        save_to_history(current_tasks[task_id])


async def process_parse_task(task_id: str, input_path: str):
    """Фоновая задача парсинга - ДЛЯ СТРАНИЦЫ ПАРСЕРА"""
    try:
        add_log_to_task(task_id, "🔍 Начинаем парсинг файлов...", "info")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            parse_files_task,
            input_path,
            task_id
        )

        task_results[task_id] = result
        current_tasks[task_id]["status"] = "completed"
        current_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        current_tasks[task_id]["result"] = result
        
        add_log_to_task(task_id, "✅ Парсинг завершен!", "success")
        
        # Сохраняем в историю
        save_to_history(current_tasks[task_id])

    except Exception as e:
        logger.error(f"Ошибка в process_parse_task: {e}")
        add_log_to_task(task_id, f"❌ Ошибка: {str(e)}", "error")
        current_tasks[task_id]["status"] = "failed"
        current_tasks[task_id]["error"] = str(e)
        current_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        # Сохраняем в историю даже при ошибке
        save_to_history(current_tasks[task_id])


# ========== ЭНДПОИНТЫ ДЛЯ ОТСЛЕЖИВАНИЯ ==========

@app.get("/api/task/{task_id}/logs")
async def get_task_logs(task_id: str):
    """Получение логов задачи"""
    if task_id not in current_tasks:
        # Проверяем историю
        history_data = load_history_from_file()
        history_task = next((h for h in history_data if h.get("taskId") == task_id), None)
        
        if history_task:
            return {
                "task_id": task_id,
                "status": history_task.get("status", "completed"),
                "type": history_task.get("type"),
                "folder_name": history_task.get("folderName"),
                "started_at": history_task.get("startTime"),
                "completed_at": history_task.get("endTime"),
                "logs": history_task.get("logs", [])
            }
        
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task_info = current_tasks[task_id].copy()
    logs = task_info.get("logs", [])

    # Преобразуем логи в правильный формат
    formatted_logs = []
    for log in logs:
        if hasattr(log, 'dict'):
            formatted_logs.append(log.dict())
        elif isinstance(log, dict):
            formatted_logs.append(log)
        else:
            formatted_logs.append({
                "message": str(log),
                "type": "info",
                "timestamp": datetime.now().isoformat()
            })

    return {
        "task_id": task_id,
        "status": task_info.get("status", "unknown"),
        "type": task_info.get("type"),
        "folder_name": task_info.get("folder_name"),
        "started_at": task_info.get("started_at"),
        "completed_at": task_info.get("completed_at"),
        "logs": formatted_logs
    }


@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Получение статуса задачи"""
    if task_id not in current_tasks:
        # Проверяем историю
        history_data = load_history_from_file()
        history_task = next((h for h in history_data if h.get("taskId") == task_id), None)
        
        if history_task:
            return {
                "task_id": task_id,
                "status": history_task.get("status", "completed"),
                "type": history_task.get("type"),
                "started_at": history_task.get("startTime"),
                "completed_at": history_task.get("endTime"),
                "has_result": True
            }
        
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return {
        "task_id": task_id,
        "status": current_tasks[task_id].get("status", "unknown"),
        "type": current_tasks[task_id].get("type"),
        "started_at": current_tasks[task_id].get("started_at"),
        "completed_at": current_tasks[task_id].get("completed_at"),
        "has_result": task_id in task_results
    }


@app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Получение результата задачи"""
    if task_id not in task_results:
        raise HTTPException(status_code=404, detail="Результат не найден")

    return {
        "task_id": task_id,
        "result": task_results[task_id],
        "retrieved_at": datetime.now().isoformat()
    }


@app.get("/api/tasks")
async def get_all_tasks():
    """Получение списка всех задач"""
    tasks = []
    for task_id, task_info in current_tasks.items():
        tasks.append({
            "id": task_id,
            "status": task_info.get("status", "unknown"),
            "type": task_info.get("type"),
            "folder_name": task_info.get("folder_name"),
            "started_at": task_info.get("started_at"),
            "logs_count": len(task_info.get("logs", []))
        })

    return {"tasks": tasks}


@app.get("/api/history")
async def get_processing_history():
    """Получение истории обработки"""
    try:
        # Загружаем историю из файла
        history_data = load_history_from_file()
        
        # Добавляем текущие задачи в историю для отображения
        for task_id, task_info in current_tasks.items():
            if task_info.get("status") == "running":
                # Проверяем, есть ли уже эта задача в истории
                existing_index = next(
                    (i for i, h in enumerate(history_data) 
                     if h.get("taskId") == task_id), 
                    -1
                )
                
                if existing_index == -1:
                    # Создаем запись для текущей задачи
                    history_entry = {
                        "id": task_id,
                        "taskId": task_id,
                        "type": task_info.get("type"),
                        "status": "running",
                        "folderName": task_info.get("folder_name"),
                        "path": task_info.get("path"),
                        "startTime": task_info.get("started_at"),
                        "endTime": None,
                        "duration": None,
                        "error": None,
                        "result": None,
                        "logs": [
                            {
                                "message": log.message if hasattr(log, 'message') else str(log),
                                "type": log.type if hasattr(log, 'type') else "info",
                                "timestamp": log.timestamp if hasattr(log, 'timestamp') else task_info.get("started_at")
                            }
                            for log in task_info.get("logs", [])
                        ]
                    }
                    history_data.insert(0, history_entry)
                else:
                    # Обновляем логи текущей задачи
                    history_data[existing_index]["logs"] = [
                        {
                            "message": log.message if hasattr(log, 'message') else str(log),
                            "type": log.type if hasattr(log, 'type') else "info",
                            "timestamp": log.timestamp if hasattr(log, 'timestamp') else task_info.get("started_at")
                        }
                        for log in task_info.get("logs", [])
                    ]
        
        # Сортируем по времени (новые сверху)
        history_data.sort(key=lambda x: x.get("startTime") or "", reverse=True)
        
        logger.info(f"Отправлена история: {len(history_data)} записей")
        
        return {
            "history": history_data,
            "count": len(history_data),
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения истории: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)