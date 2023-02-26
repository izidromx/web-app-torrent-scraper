import requests
from bs4 import BeautifulSoup
import asyncio
import aiohttp
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    s = request.args.get('search')
    url = f"http://www.omdbapi.com/?s={s}&apikey=YOUR_OMDB_API_KEY"
    response = requests.get(url)
    data = response.json()
    movies = data.get("Search")
    return render_template("index.html", movies=movies)


@app.route('/get_movie/<single_title>', methods=['GET', 'POST'])
def get_movie(single_title):
    url = f"http://www.omdbapi.com/?t={single_title}&apikey=YOUR_OMDB_API_KEY"
    response = requests.get(url)
    movie_data = response.json()

    movies = []
    stream_links = []
    if request.method == "POST":
        scrape_title = request.form['scrape-title']
        scrape_title = scrape_title.replace(" ", "+")
        url = f'https://torrentz2.nz/search?q={scrape_title}'

        page = requests.get(url)
        print(page.url)
        soup = BeautifulSoup(page.content, 'html.parser')

        container = soup.find('div', class_='results')
        movie_elements = container.find_all('dl')

        magnets = []
        for movie_element in movie_elements:
            title_node = movie_element.find('dt')
            title = title_node.find('a').text
            stats = movie_element.find('dd')
            size = stats.contents[2].text
            seeds = stats.contents[3].text
            leecher = stats.contents[4].text
            date = stats.contents[1].text

            magnet_node = stats.contents[0]
            magnet = magnet_node.find("a").get("href")

            movie = {
                'title': title,
                'size': size,
                'seeds': seeds,
                'leecher': leecher,
                'date': date,
                'magnets': magnets.append(magnet)
            }

            movies.append(movie)

        api_key = "YOUR_REAL_DEBRID_API_KEY"
        headers = {"Authorization": f"Bearer {api_key}"}

        magnet_links = magnets
        torrent_ids = []

        async def add_magnet(link):
            payload = {"magnet": link}
            url = f"https://api.real-debrid.com/rest/1.0/torrents/addMagnet?"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=payload) as response:
                    data = await response.json()
                    torrent_id = data.get("id")
                    torrent_ids.append(torrent_id)

        async def select_files(magnet_id):
            payload = {"files": "all"}
            url = f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{magnet_id}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=payload) as response:
                    pass

        async def get_links(magnet_id):
            url = f"https://api.real-debrid.com/rest/1.0/torrents/info/{magnet_id}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    data = await response.json()
                    link = data["links"]
                    return link

        async def unrestrict(link):
            payload = {"link": link}
            url = "https://api.real-debrid.com/rest/1.0/unrestrict/link?"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(url, data=payload) as response:
                    data = await response.json()
                    stream_link = data.get("download")
                    if stream_link is not None:
                        stream_links.append(stream_link)

        async def add_all(magnet_links):
            tasks = []
            for link in magnet_links:
                tasks.append(asyncio.create_task(add_magnet(link)))
            await asyncio.gather(*tasks)

        async def select_all(torrent_ids):
            tasks = []
            for magnet_id in torrent_ids:
                tasks.append(asyncio.create_task(select_files(magnet_id)))
            await asyncio.gather(*tasks)

        async def get_all(torrent_ids):
            tasks = []
            for magnet_id in torrent_ids:
                tasks.append(asyncio.create_task(get_links(magnet_id)))
            return await asyncio.gather(*tasks)

        async def unrestrict_all(links):
            tasks = []
            for link in links:
                tasks.append(asyncio.create_task(unrestrict(link)))
            await asyncio.gather(*tasks)

        async def main(magnet_links):
            await add_all(magnet_links)
            await select_all(torrent_ids)
            links = await get_all(torrent_ids)
            await unrestrict_all(links)

        asyncio.run(main(magnet_links))
    stream_movie_info = zip(stream_links, movies)
    return render_template('movie.html', stream_links=stream_links, movies=movies, movie_data=movie_data,
                           stream_movie_info=stream_movie_info)


if __name__ == "__main__":
    app.run(debug=True)
