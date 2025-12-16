import asyncio
import os
import shutil
import re
import pandas as pd
from io import StringIO
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
import logging
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальное хранилище задач
current_tasks: Dict[str, Dict] = {}
task_results: Dict[str, Dict] = {}


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


# Вспомогательные функции
def add_log_to_task(task_id: str, message: str, type: str = "info"):
    """Добавляет лог в задачу"""
    if task_id not in current_tasks:
        current_tasks[task_id] = {"logs": [], "status": "running"}

    # Добавляем timestamp к сообщению
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"

    current_tasks[task_id]["logs"].append(LogMessage(message=formatted_message, type=type))

    # Ограничиваем количество логов (последние 1000)
    if len(current_tasks[task_id]["logs"]) > 1000:
        current_tasks[task_id]["logs"] = current_tasks[task_id]["logs"][-1000:]


# ========== ФУНКЦИИ ОБРАБОТКИ ФАЙЛОВ ==========

def find_all_broken_files(root_path: str, task_id: str):
    """Находит ВСЕ битые .tst файлы без парных .txt во ВСЕХ вложенных папках"""
    add_log_to_task(task_id, "🔍 НАЧИНАЕМ РЕКУРСИВНЫЙ ПОИСК ВО ВСЕХ ПАПКАХ...", "info")
    add_log_to_task(task_id, "============================================", "info")

    total_found = 0
    total_processed = 0
    moved_files = []

    def walk(directory):
        """Рекурсивный обход всех папок"""
        for root, dirs, files in os.walk(directory):
            yield root, dirs, files

    for folder, dirs, files in walk(root_path):
        # Пропускаем папку "Изолированные_Битые" если она существует
        if "Изолированные_Битые" in folder:
            continue
            
        add_log_to_task(task_id, f"📁 Проверка папки: {os.path.basename(folder)}", "info")

        tst_files = sorted([f for f in files if f.lower().endswith(".tst")])
        
        if not tst_files:
            add_log_to_task(task_id, "   → .tst файлов не найдено", "info")
            continue
            
        add_log_to_task(task_id, f"   → .tst найдено: {len(tst_files)}", "info")

        folder_found = 0
        for tst in tst_files:
            total_processed += 1
            base = os.path.splitext(tst)[0]
            txt = base + ".txt"
            txt_path = os.path.join(folder, txt)

            if not os.path.exists(txt_path):
                # Найден битый файл
                src = os.path.join(folder, tst)
                dest_dir = os.path.join(root_path, "Изолированные_Битые")
                os.makedirs(dest_dir, exist_ok=True)
                
                # Создаем подпапку с именем оригинальной папки
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

                    add_log_to_task(task_id, "--- ❌ БИТЫЙ ФАЙЛ НАЙДЕН ---", "warning")
                    add_log_to_task(task_id, f"   Файл: {tst}", "success")
                    add_log_to_task(task_id, f"   Папка: {os.path.basename(folder)}", "info")
                    add_log_to_task(task_id, f"   Причина: нет {txt}", "info")
                    add_log_to_task(task_id, f"   Перемещён в: {dest_dir}", "info")
                    add_log_to_task(task_id, "---------------------------", "info")

                except Exception as e:
                    add_log_to_task(task_id, f"   ❌ Ошибка перемещения: {e}", "error")
                    
        if folder_found > 0:
            add_log_to_task(task_id, f"   ✅ В папке найдено битых: {folder_found}", "success")

    if total_found > 0:
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, f"🎉 ПОИСК ЗАВЕРШЕН! НАЙДЕНО: {total_found} БИТЫХ ФАЙЛОВ", "success")
        add_log_to_task(task_id, f"📊 Обработано всего файлов: {total_processed}", "info")
        add_log_to_task(task_id, f"📁 Перемещено в: {os.path.join(root_path, 'Изолированные_Битые')}", "info")
        add_log_to_task(task_id, "=" * 50, "info")
        
        return {
            "found": total_found,
            "processed": total_processed,
            "moved_files": moved_files,
            "target_folder": os.path.join(root_path, "Изолированные_Битые"),
            "message": f"Найдено {total_found} битых файлов"
        }
    else:
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, "✅ ПОИСК ЗАВЕРШЕН!", "success")
        add_log_to_task(task_id, f"📊 Обработано файлов: {total_processed}", "info")
        add_log_to_task(task_id, "📭 БИТЫХ ФАЙЛОВ НЕ НАЙДЕНО", "success")
        add_log_to_task(task_id, "=" * 50, "info")
        
        return {
            "found": 0,
            "processed": total_processed,
            "message": "Битых файлов не обнаружено"
        }


def parse_files_task(input_folder: str, task_id: str):
    """Парсит файлы в указанной папке"""
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
        "УльтраЗвук файлы": 0,
        "UCA - неполные/ошибки": 0,
        "Ошибки чтения": 0,
        "Распределение по категориям UCA": {}
    }

    # Функции парсинга (остаются без изменений)
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

                if not missing_params:
                    density_folder = get_density_range(density_val)
                    algorithm_folder = get_strength_type(strength_val)
                    cement_folder = get_cement_class(cement_val)
                    
                    # Сохраняем структуру папок
                    if relative_root != ".":
                        target_folder = os.path.join(output_folder, relative_root, density_folder, algorithm_folder, cement_folder)
                    else:
                        target_folder = os.path.join(output_folder, density_folder, algorithm_folder, cement_folder)
                        
                    category_key = f"{density_folder}/{algorithm_folder}/{cement_folder}"
                    add_log_to_task(task_id,
                                    f"✅ Категория: Плотность={density_folder}, Прочность={algorithm_folder}, Цемент={cement_folder}",
                                    "success")
                else:
                    target_folder = os.path.join(output_folder, relative_root, "Неполные")
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

                    target_folder = os.path.join(output_folder, relative_root, "Неполные")
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

            # --- ОБРАБОТКА НЕ-UCA (УльтраЗвук) ---
            else:
                report_summary["УльтраЗвук файлы"] += 1
                add_log_to_task(task_id, "➡️ Тип определен: УльтраЗвук", "info")

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

                # Сохраняем структуру папок
                if relative_root != ".":
                    ultrasound_folder = os.path.join(output_folder, relative_root, "УльтраЗвук")
                else:
                    ultrasound_folder = os.path.join(output_folder, "УльтраЗвук")
                    
                os.makedirs(ultrasound_folder, exist_ok=True)

                base_name = os.path.splitext(file_name)[0]
                excel_path = os.path.join(ultrasound_folder, f"{base_name}.xlsx")
                df.to_excel(excel_path, index=False)

                add_log_to_task(task_id, f"💾 Сохранено в {ultrasound_folder}", "success")

        # Итоговый отчет
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, "🎉 ИТОГОВЫЙ ОТЧЕТ", "success")
        add_log_to_task(task_id, "=" * 50, "info")
        add_log_to_task(task_id, f"📁 Всего обработано: {report_summary['Всего обработано']}", "info")
        add_log_to_task(task_id, f"🔹 UCA-файлы: {report_summary['UCA файлы']}", "info")
        add_log_to_task(task_id, f"🔹 УльтраЗвук: {report_summary['УльтраЗвук файлы']}", "info")
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
            "started_at": datetime.now().isoformat()
        }

        add_log_to_task(task_id, f"📁 Обрабатываем папку: {os.path.basename(input_path)}", "info")
        add_log_to_task(task_id, "⏳ Начинаем поиск битых файлов...", "info")

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
            "started_at": datetime.now().isoformat()
        }

        add_log_to_task(task_id, f"📁 Обрабатываем папку: {os.path.basename(input_path)}", "info")
        add_log_to_task(task_id, "⏳ Начинаем парсинг...", "info")

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
    """Фоновая задача поиска битых файлов - ДЛЯ ГЛАВНОЙ СТРАНИЦЫ"""
    try:
        add_log_to_task(task_id, "🔍 Начинаем поиск битых .tst файлов...", "info")

        # Запускаем обработку в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            find_all_broken_files,  # ИСПРАВЛЕНО: используем новую функцию
            input_path,
            task_id
        )

        # Сохраняем результат
        task_results[task_id] = result

        # Отмечаем задачу как завершенную
        current_tasks[task_id]["status"] = "completed"
        current_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        current_tasks[task_id]["result"] = result

        add_log_to_task(task_id, "✅ Задача поиска завершена!", "success")

    except Exception as e:
        logger.error(f"Ошибка в process_find_broken_task: {e}")
        add_log_to_task(task_id, f"❌ Ошибка: {str(e)}", "error")
        current_tasks[task_id]["status"] = "failed"
        current_tasks[task_id]["error"] = str(e)


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

    except Exception as e:
        logger.error(f"Ошибка в process_parse_task: {e}")
        add_log_to_task(task_id, f"❌ Ошибка: {str(e)}", "error")
        current_tasks[task_id]["status"] = "failed"
        current_tasks[task_id]["error"] = str(e)


# ========== ЭНДПОИНТЫ ДЛЯ ОТСЛЕЖИВАНИЯ ==========

@app.get("/api/task/{task_id}/logs")
async def get_task_logs(task_id: str):
    """Получение логов задачи"""
    if task_id not in current_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    task_info = current_tasks[task_id].copy()
    logs = task_info.get("logs", [])

    return {
        "task_id": task_id,
        "status": task_info.get("status", "unknown"),
        "type": task_info.get("type"),
        "folder_name": task_info.get("folder_name"),
        "started_at": task_info.get("started_at"),
        "completed_at": task_info.get("completed_at"),
        "logs": [log.dict() for log in logs]
    }


@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Получение статуса задачи"""
    if task_id not in current_tasks:
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)