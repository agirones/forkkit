from requests_html import HTMLSession
import sys
from models import Reviews
from peewee import IntegrityError


sess = HTMLSession()
RECURSION_DEPTH = 1


def scrape_urls(url):
    if isinstance(url, list):
        # in this case, flatten
        links = []
        for u in url:
            print(u)
            links += list(scrape_urls(u))
        return filter(lambda x: "/reviews/albums" in x and "?" not in x, links)
    resp = sess.get(url)
    links = resp.html.absolute_links
    return filter(lambda x: "/reviews/albums" in x and "?" not in x, links)


def scrape_page(url, recur_depth=0):
    data = {'uri': url}
    resp = sess.get(url)
    score = resp.html.find('.score')
    if score:
        data['score'] = score[0].text
    genre = resp.html.find('.genre-list__link')
    if genre:
        data['genre'] = genre[0].text
    title = resp.html.find('title')[0].text
    data['title'] = title
    if title:
        print(title)
        try:
            data['artist'] = title.split(":")[0]
            data['album'] = title[title.index(":")+1:title.index("Album Review")].strip()
        except ValueError:
            return
    yield(data)
    if recur_depth > 0:
        links = filter(lambda x: "/reviews/albums"in x and "?" not in x,
                       resp.html.absolute_links)
        for link in links:
            for page in scrape_page(link, recur_depth=recur_depth - 1):
                yield(page)


def insert_review(data):
    new_review = Reviews(artist=data['artist'], album=data['album'])
    try:
        new_review.title = data['title']
    except KeyError:
        pass
    try:
        new_review.score = data['score']
    except KeyError:
        pass
    try:
        new_review.genre = data['genre']
    except KeyError:
        pass
    try:
        new_review.uri = data['uri']
    except KeyError:
        pass
    new_review.save()


if __name__ == "__main__":
    default_link = 'https://pitchfork.com/best/high-scoring-albums/?page='
    try:
        if "pitchfork.com" in sys.argv[1]:
            link = sys.argv[1]
        elif isinstance(sys.argv[1], int):
            link = [default_link + str(i) for i in range(sys.argv[1])]
    except IndexError:
        link = [default_link + str(i) for i in range(1, 10)]
    for url in scrape_urls(link):
        for data in scrape_page(url, recur_depth=RECURSION_DEPTH):
            try:
                insert_review(data)
            except IntegrityError:
                pass
            print(data)
