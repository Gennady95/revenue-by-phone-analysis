import pandas as pd, time, re, glob, getpass, platform, telebot
from sqlalchemy import create_engine
from datetime import datetime
from tqdm import tqdm

#Паттерны
engine = create_engine(os.getenv("DB_URL"))
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
chat_id = os.getenv("CHAT_ID")
re_1 = r'[^0-9,.;/]'                                                                                                     # Регулярное выражение для отсева букв, пробелов
re_2 = r'[^0-9]'                                                                                                         # Регулярное выражение для отсева знаков

def SendTelegram(status):
	# Получение информации о компьютере
	UserName = getpass.getuser()                                                                                         # Имя пользователя (обычно оно User - не информативно)
	CompName = platform.node()                                                                                           # Имя компьютера
	chat_id = '5249664773'                                                                                               # ID моей телеги
	if status == "try": # Если связь с телегой установлена
		bot.send_message(chat_id, date+" пользователь "+UserName+" ("+CompName+") успешно воспользовался скриптом для подсчёта выручки по номерам телефонов") #Отправка сообщения
	elif status == "except1": # Если нет подключения к SQL серверу
		bot.send_message(chat_id, "ERROR: " + date+" пользователь "+UserName+" ("+CompName+") неудачно запустил скрипт для подсчёта выручки по номерам телефонов - не подключил VPN") #Отправка сообщения
	elif status == "except2": # Если нет подключения к SQL серверу
		bot.send_message(chat_id, "ERROR: " + date+" пользователь "+UserName+" ("+CompName+") неудачно запустил скрипт для подсчёта выручки по номерам телефонов - либо не закрыл файл, либо в файле нет подходящих колонок") #Отправка сообщения

def CollectData(FileLocation):                                                                                           # Чтение одного или нескольких excel фалов .xlsx
	GroupFile = [item for item in glob.glob(FileLocation)]                                                               # Собираем файлы в список
	itter = 0                                                                                                            # Переменная для подсчёта удачных повторений скрипта
	for Filename in tqdm(GroupFile): # Вводные для progress bar
		if not 'Результат валидации' in str(Filename):
			print(Filename, "Началась загрузка excel файла: ", datetime.time(datetime.now()))
			try:
				File = pd.read_excel(Filename, usecols=['Номер телефона', 'Дата начала', 'Дата конца'])                  # Чтение excel-файла
				dfEX = pd.DataFrame(File)                                                                                # Формирование dataframe
				#Обработка фрейма данных
				dfEX['Дата начала'] = pd.to_datetime(dfEX['Дата начала'], dayfirst=True)                                 # Преобразование столбца дат в даты SQL формата
				dfEX['Дата конца'] = pd.to_datetime(dfEX['Дата конца'], dayfirst=True)                                   # Преобразование столбца дат в даты SQL формата
				dfEX['Номер телефона'].astype('str')                                                                     # Преобразование столбца с номерами телефонов в строчный формат
				dfEX['Номер телефона'] = dfEX['Номер телефона'].apply(lambda x: max(re.sub(re_2, ',', re.sub(re_1, '', str(x))).lstrip(',').split(',', 10), key=len)[-10:])
				dfEX['Номер телефона'] = dfEX['Номер телефона'].loc[dfEX['Номер телефона'].str.len().between(10, 11)]    # Выбор номера телефона определённого формата
				dfEX = dfEX.groupby(pd.Grouper(key='Номер телефона')).min().reset_index()                                # Группировка с удалением дубликатов и выбором наименьшей даты
				# Создание списков для итерирования
				list_of_numbers = list(filter(None, dfEX['Номер телефона'].tolist()))                                    # Получение списка из номеров телефонов в excel файле
				list_of_date_start = list(filter(None, dfEX['Дата начала'].tolist()))                                    # Получение списка из номеров дат начала в excel файле
				list_of_date_finish = list(filter(None, dfEX['Дата конца'].tolist()))                                    # Получение списка из дат окончания в excel файле
				first_date = min(list_of_date_start); end_date = max(list_of_date_finish)                                # Присвоение нижней и верхней границы из списка (для обрезки базы)
				print("Созданы списки для проверки по файлу " + FileLocation + " . Теперь начнём считать...")
				# Анализ по базе розничных магазинов
				dfSQLmagNew = dfSQLmag.loc[((dfSQLmag['Дата'] >= first_date) & (dfSQLmag['Дата'] <= end_date))]          # Обрезка базы по датам
				dfSQLmagNew = dfSQLmagNew.loc[(dfSQLmagNew['НомерТелефона'].isin(list(filter(None, list_of_numbers))))]  # Обрезка базы магазина по номерам телефонов
				print("В базе розницы " + str(len(dfSQLmagNew['НомерТелефона'])) + " подходящих записей по номерам телефонов")
				for Num, Start, End in zip(list_of_numbers, list_of_date_start, list_of_date_finish):                    # Цикл проходит по списку SQL n количество раз, равному len(list) базы excel
					dfSQLmagNew.loc[((dfSQLmagNew['НомерТелефона'].isin(list(filter(None, Num)))) & (dfSQLmagNew['Дата'] >= Start) & (dfSQLmagNew['Дата'] <= End))] # Формат для сегодняшней даты np.datetime64(datetime.now())
				dfSQLmagTT = dfSQLmagNew.groupby('ТТ').agg({'Сумма': ['sum', 'count'], 'Прибыль': ['sum']}).reset_index() # Группировка с удалением дубликатов и выбором наименьшей даты
				# Анализ по базе СТО
				dfSQLstoNew = dfSQLsto.loc[((dfSQLsto['Дата'] >= first_date) & (dfSQLsto['Дата'] <= end_date))]          # Обрезка базы по датам
				dfSQLstoNew = dfSQLstoNew.loc[(dfSQLstoNew['НомерТелефона'].isin(list(filter(None, list_of_numbers))))]  # Обрезка базы СТО по номерам телефонов
				print("В базе СТО " + str(len(dfSQLstoNew['НомерТелефона'])) + " подходящих записей по номерам телефонов")
				for Num, Start, End in zip(list_of_numbers, list_of_date_start, list_of_date_finish):                    # Цикл проходит по списку SQL n количество раз, равному len(list) базы excel
					dfSQLstoNew.loc[((dfSQLstoNew['НомерТелефона'].isin(list(filter(None, Num)))) & (dfSQLstoNew['Дата'] >= Start) & (dfSQLstoNew['Дата'] <= End))] # Формат для сегодняшней даты np.datetime64(datetime.now())
				dfSQLstoTT = dfSQLstoNew.groupby('ТТ').agg({'Сумма': ['sum', 'count'], 'Прибыль': ['sum']}).reset_index() # Группировка с удалением дубликатов и выбором наименьшей даты
				try:
					with pd.ExcelWriter(Filename, engine='openpyxl', mode='a') as writer:                                # Дополнение excel файла новыми листами
						try:
							dfSQLmagNew.to_excel(writer, sheet_name='Транзакции розницы', index=False)
							dfSQLstoNew.to_excel(writer, sheet_name='Транзакции СТО', index=False)
							dfSQLmagTT.to_excel(writer, sheet_name='Группировка по магазинам')
							dfSQLstoTT.to_excel(writer, sheet_name='Группировка по СТО')
							itter += 1
						except: pass
				except:	print("В файле" + Filename + " уже присутствуют листы с аналитикой :("); time.sleep(5)
			except Exception as e:
				print(f'Произошла ошибка: {e}'); print("Возможно у Вас открыт excel файл, который Вы пытаетесь валидировать или колонки названы неправильно"); time.sleep(5) #Обработка ошибки

	print("Все файлы обработаны")
	if itter > 0: SendTelegram("try")
	else: SendTelegram("except2")

#Получение данных из SQL
try:
	lightquery_1 = "SELECT * FROM sales_parts"                                                                           # SQL запрос в базу РОЗНИЦЫ
	lightquery_2 = "SELECT * FROM sales_sto"                                                                             # SQL запрос в базу СТО
	print("Начинается загрузка SQL базы розницы (может занять пару минут)..."); dfSQLmag = pd.read_sql(lightquery_1, engine); print("База по рознице загружена") # Чтение MySQL РОЗНИЦЫ, получение dataframe
	print("Начинается загрузка SQL базы СТО (может занять пару минут)..."); dfSQLsto = pd.read_sql(lightquery_2, engine); print("База по СТО загружена") # Чтение MySQL СТО, получение dataframe
	print("Начинается конвертация номеров телефонов в БД")
	dfSQLmag['НомерТелефона'] = dfSQLmag['НомерТелефона'].apply(lambda x: re.sub(re_1, '', str(x)))                 # Чистка БД РОЗНИЦЫ для подготовки к поиску
	dfSQLsto['НомерТелефона'] = dfSQLsto['НомерТелефона'].apply(lambda x: re.sub(re_1, '', str(x)))                 # Чистка БД СТО для подготовки к поиску
	print("Конвертация номеров телефонов в БД завершена, теперь возмусь за ваши файлы")
except Exception:
	print("Не могу подключится к SQL серверу. Проверьте подключение к VPN и перезапустите приложение")
	SendTelegram("except1")
	time.sleep(5); exit()

CollectData('*.xlsx')
