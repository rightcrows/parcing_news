from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.common.exceptions import *
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import time


def open_csv_file(path):
    """ Функция для открытия csv файла для записи
    в utf-8 кодировке.
    :param path: путь к csv файлу
    :return: поток, для записи данных в файл
    """
    while True:
        try:
            return open(path, mode='w', encoding='utf-8')
        except PermissionError:
            print('Файл невозможно открыть!')


def add_proxy(capabilities):
    """ Функция для добавления прокси в браузер.
    Вызов этой функции закоментил, так как не стал
    искать подходящий ip для прокси.
    :param capabilities: настройки браузера
    :return: измененные настройки браузера
    """
    proxy = ''  # Ip для прокси
    capabilities['marionette'] = True
    capabilities['proxy'] = {
        "proxyType": "MANUAL",
        "httpProxy": proxy,
        "ftpProxy": proxy,
        "sslProxy": proxy
    }


def get_html_from_element(url, xpath):
    """ Функция для получения html кода web-элемента, найденного
    с помощью его xPath в url странице.
    :param url: web-адрес ресурса в сети
    :param xpath: путь к web-элементу, у которого нужно получить html-код.
    :return: html-код пригодный для дальнейшего парсинга под soup4
    """
    while True:
        try:
            driver.get(url)
            html_selenium = driver.find_element(By.XPATH, xpath).get_attribute('innerHTML')
            return BeautifulSoup(html_selenium, "html.parser")
        except Exception as ex:
            input(ex)
            print('Страница не загружена! Проверьте интернет подключение или настройки прокси!')


def parcing_comments(name_article):
    """ Функция парсит комментарии на странице со статьей. Собираются:
    имя автора, дата публикации, текст собщения и было ли кому-то отправлено ответом.
    Также фиксируется название статьи в записи, чтобы была связь комментария со статьей.
    :param name_article: название статьи, на странице которой парсятся комментарии.
    :return: ничего, по окончанию парсинга странице все комментарии записываются в
    csv файл.
    """
    # Пролистывание страницы до блока с комментариями и нажатие на "еще комментарии"
    action.move_to_element(driver.find_element_by_id("zkn_comments")).perform()
    time.sleep(1)
    while True:
        try:
            driver.find_element(By.XPATH, '//a[@class="zknc znkc-load-more-link"]').click()
        except NoSuchElementException:
            break
        except (ElementClickInterceptedException, StaleElementReferenceException):
            pass

    # Получение html кода блока, в котором хранятся комменты
    html_with_comments = BeautifulSoup(driver.page_source, "html.parser").find('div', {'class': 'zknc zknc-posts'})

    # Получение списка комментарий и его разбиение на каждый по отдельности
    list_comments = html_with_comments.find_all('div', {'class': 'zknc zknc-item'})
    for comment in list_comments:
        # Парсинг комментарий
        name_author = comment.find('a', {'class': 'zknc zknc-author-name'}).text
        date_publication = comment.find('span', {'class': 'zknc zknc-date'})['title']
        message = comment.find('div', {'class': 'zknc zknc-message'}).text
        answer = comment.find('span', {'class': 'zknc zknc-answer-to'}).text
        if '»' in answer:
            answer = answer.split('»  ')[1]
        writer_comments.writerow({'name_author': name_author, 'date_publication': date_publication,
                        'text_comment': message, 'answer_to': answer, 'name_article': name_article})


# Открытие csv файла, и использование класса DictWriter, для записи данных в поток в виде словаря
csv_file = open_csv_file('news.csv')
fieldnames = ['name_article', 'date_publication', 'text_article', 'count_commentaries']
writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
writer.writeheader()
csv_file_comments = open_csv_file('comments.csv')
fieldnames_comments = ['name_author', 'date_publication', 'text_comment', 'answer_to', 'name_article']
writer_comments = csv.DictWriter(csv_file_comments, fieldnames=fieldnames_comments)
writer_comments.writeheader()

# Вытаскивание настройк браузера для добавления прокси и инициализация самого браузера
caps = webdriver.DesiredCapabilities.CHROME
# add_proxy(caps)
driver = webdriver.Chrome(desired_capabilities=caps)
action = ActionChains(driver)
driver.implicitly_wait(1)

# Вытаскивание сегодняшней даты в строковом формате, понадобится в дальнейшем парсинге,
#   для получения полной даты публикации новости.
day_publication = datetime.today().strftime("%Y-%m-%d")

# Получение html-кода web-элемента, хранящий список публикаций на сайте.
site = 'https://www.zakon.kz/news'
html_with_news = get_html_from_element(site, '//div[@id="dle-content"]')

# Получение списка публикаций и его разбиение на каждую по отдельности
list_news = html_with_news.find_all('div', {'class': 'cat_news_item'})
for news in list_news:
    # Проверка на наличие ссылки на статью, если такой не имеется,
    if not news.find('a'):
        # Изменение дня публикации
        day_publication = news.find('span').text
        continue

    # Парсинг данных: название статьи, время публикации, количество комментарий и ссылку на статью
    name = news.find('a').text
    time_publication = news.find('span').text
    href_article = news.find('a')['href']
    count_commentaries = 0 if len(news.find_all('span')) == 1 else int(news.find_all('span')[1].text)
    text_article = ''

    # Получение html-кода web-элемента, хранящий текст статьи.
    html_article = get_html_from_element(site + href_article, '//div[@class="fullnews white_block"]')

    # Получение всех дочерних элементов и
    children = html_article.findChildren()
    for child in children:
        # Пропускать все элементы, не являющийся текстом статьи
        if child.name not in ['p', 'blockquote']:
            continue

        # Остановка парсинга на конце статьи
        if child.get('id') == 'tg_invite':
            break
        text_article += str(child.text)

    # Объединение времени и дня публикации статьи
    str_date = day_publication + ' ' + time_publication
    datetime_publication = datetime.strptime(str_date, '%Y-%m-%d %H:%M')

    # Запись в csv файл
    writer.writerow({'name_article': name, 'date_publication': datetime_publication,
                     'text_article': text_article, 'count_commentaries': count_commentaries})

    # Парсинг комментарий, если есть хотя бы один комментарий
    parcing_comments(name) if count_commentaries > 0 else None
csv_file_comments.close()
csv_file.close()
driver.close()
