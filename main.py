from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from datetime import datetime
import csv
import requests


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


def get_html_from_element(url, tag, attr, value):
    """ Функция для получения html кода web-элемента, найденного
    с помощью его xPath в url странице.
    :param url: web-адрес ресурса в сети.
    :param tag: тэг, у которого нужно получить html-код.
    :param attr: аттрибут тэга, которого нужно найти.
    :param value: значение аттрибута.
    :return: html-код пригодный для дальнейшего парсинга под soup4
    """
    while True:
        try:
            response = requests.get(url, timeout=(10, 0.2), headers={'User-Agent': UserAgent().chrome})
            html_page = BeautifulSoup(response.text, "html.parser")
            return html_page.find(tag, {attr: value})
        except Exception as ex:
            print(ex)
            print('Страница не загружена! Проверьте интернет-соединение или настройки прокси!')


def parcing_comments(name_article, url):
    """ Функция парсит комментарии на странице статьи.
    :param name_article: название статьи.
    :param url: ссылка на статью.
    """
    # Заголовок и данные для post-запроса, чтобы получить комментарии
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    id_article = url.split('news/')[1].split('-')[0]
    payload = {'page_title': name_article,
               'page_url': url,
               'block_code': 'zakonnewsid' + id_article
               }

    # url для загрузки с сервера комментарии
    comment_url = 'https://zcomments.net/service/init/1'

    # Загрузка комментарий с сервера по статье
    with requests.Session() as session:
        response = session.post(comment_url, headers=headers, data=payload)

    # Парсинг комментарий
    for comment in response.json()['comments']['items']:
        parcing_comment(comment, id_article)


def parcing_comment(comment, id_article):
    """ Парсит комментарий, если есть ответы на этот комментарий,
    отправляет их на парсинг.
    :param comment: комментарий для парсинга.
    :param id_article: id статьи, в котором расположен комментарий.
    """
    print('Имя автора:', comment['user_nick'])
    print('ID автора:', comment['user_id'])
    print('Дата публикации:', comment['created_at'])
    print('ID комментария:', comment['id'])
    print('Комментарий:', comment['message'])
    print('Ответ к комментарию ID:', comment['answer_to_comment_id'])
    print('Понравилось людям:', comment['vote'])
    print('Количество голосов:', comment['likes'])
    print('ID новости:', id_article)
    print('-----------------------------')
    writer_comments.writerow({'name_author': comment['user_nick'], 'id_author': comment['user_id'],
                              'date_publication': comment['created_at'], 'id_comment': comment['id'],
                              'text_comment': comment['message'], 'answer_to': comment['answer_to_comment_id'],
                              'likes': comment['vote'], 'vote': comment['likes'], 'id_article': id_article})
    if comment['children']:
        for comment_children in comment['children']:
            parcing_comment(comment_children, id_article)


# Открытие csv файла, и использование класса DictWriter, для записи данных в поток в виде словаря
csv_file = open_csv_file('news.csv')
fieldnames = ['name_article', 'date_publication', 'text_article', 'count_commentaries']
writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
writer.writeheader()
csv_file_comments = open_csv_file('comments.csv')
fieldnames_comments = ['name_author', 'id_author', 'date_publication', 'id_comment',
                       'text_comment', 'answer_to', 'likes', 'vote', 'id_article']
writer_comments = csv.DictWriter(csv_file_comments, fieldnames=fieldnames_comments)
writer_comments.writeheader()

# Вытаскивание сегодняшней даты в строковом формате, понадобится в дальнейшем парсинге,
#   для получения полной даты публикации новости.
day_publication = datetime.today().strftime("%Y-%m-%d")

# Получение html-кода web-элемента, хранящий список публикаций на сайте.
site = 'https://www.zakon.kz/news'
html_with_news = get_html_from_element(site, 'div', 'id', 'dle-content')

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
    html_article = get_html_from_element(site + href_article, 'div', 'class', 'fullnews white_block')

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

    print('Название статьи:', name)
    print('Время публикации:', datetime_publication)
    print('Текст статьи:', text_article)
    print('Количество комментарий:', count_commentaries)
    # Запись в csv файл
    writer.writerow({'name_article': name, 'date_publication': datetime_publication,
                     'text_article': text_article, 'count_commentaries': count_commentaries})

    # Парсинг комментарий, если есть хотя бы один комментарий
    parcing_comments(name, site + href_article) if count_commentaries > 0 else None
    print('========================================')
csv_file_comments.close()
csv_file.close()
