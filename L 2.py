from bs4 import BeautifulSoup
import requests
from pathlib import Path
import json
from urllib.parse import urljoin
from pymongo import MongoClient

class JobParse:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OPR/73.0.3856.415'}
    base_url = 'https://www.superjob.ru'

    def __init__(self, start_url: str, client):
        self.start_url = start_url
        self.client = client
        self.db = self.client['vacancies']
        self.collections = self.db['vacancies_sj']
    def _get_response(self, url):
        while True:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response

    def _get_soup(self, url):
        response = self._get_response(url)
        return BeautifulSoup(response.text, 'html.parser')

    def _parse(self, vacancy):
        data = {}
        for key, funk in self._get_template().items():
            try:
                data[key] = funk(vacancy)
            except AttributeError:
                pass
        return data

    def _save(self, data: dict):
        try:
            if self.collections.count_documents({'url': data['url']}) > 0:
                pass
            else:
                self.collections.insert_one(data)
        except KeyError as err:
            self.collections.insert_one(data)
            print(err)

    def run(self):
        url = self.start_url
        cnt = 0
        while url:
            soup = self._get_soup(url)
            button = soup.find('a', attrs={'class': 'icMQ_ bs_sM _3ze9n f-test-button-dalshe f-test-link-Dalshe'})
            try:
                url = urljoin(self.base_url, button.attrs.get('href', ''))
            except AttributeError as err:
                print(err)
                url = False
            for vac in soup.find_all('div', attrs={'class': "iJCa5 f-test-vacancy-item _1fma_ undefined _2nteL"}):
                vacancies_data = self._parse(vac)
                cnt+=1
                self._save(vacancies_data)
            print(cnt)

    def _get_template(self):

        return {
            'name': lambda vac: vac.find('div', attrs={'class': "_3mfro PlM3e _2JVkc _3LJqf"}).text,
            'url': lambda vac: urljoin(self.base_url, vac.find('div', attrs={'class': "_3mfro PlM3e _2JVkc _3LJqf"}).find('a', attrs={'target': "_blank"}).attrs.get('href', '')),
            'min_sal': lambda vac: self._get_salary(vac.find('span', attrs={'class': "_1OuF_ _1qw9T f-test-text-company-item-salary"}))[0],
            'max_sal': lambda vac: self._get_salary(vac.find('span', attrs={'class': "_1OuF_ _1qw9T f-test-text-company-item-salary"}))[1],
            'valuta': self._get_valuta,
        }


    def _get_salary(self, work):
        sal = work.find('span', attrs={'class': '_3mfro _2Wp8I PlM3e _2JVkc _2VHxz'}).text
        if sal.lower()=='по договоренности':
            return None
        my_list = sal.split()
        try:
            if my_list[0].isdigit():
                min_s = float(f'{my_list[0]}{my_list[1]}')
                max_s = float(f'{my_list[3]}{my_list[4]}')
            elif my_list[0] == 'от':
                min_s = float(f'{my_list[1]}{my_list[2]}')
                max_s = None
            elif my_list[0] == 'до':
                min_s = None
                max_s = float(f'{my_list[1]}{my_list[2]}')
            else:
                min_s = None
                max_s = None
            return (min_s, max_s)
        except IndexError as err:
            print(err)
            max_s = None
            return (0, max_s)

    def _get_valuta(self, vac):
        work = vac.find('span', attrs={'class': "_1OuF_ _1qw9T f-test-text-company-item-salary"})
        sal = work.find('span', attrs={'class': '_3mfro _2Wp8I PlM3e _2JVkc _2VHxz'}).text
        if sal.lower() == 'по договоренности':
            return None
        my_list = sal.split()

        if my_list[0].isdigit() and len(my_list) > 3:
            val = my_list[5]
        elif my_list[0].lower() == 'от' or my_list[0].lower() == 'до':
            val = my_list[3]
        elif my_list[0].lower() == 'по':
            val = None
        else:
            val = 'руб'
        return val


if __name__ == '__main__':
    name = input('Введите должность: ')
    url = f'https://www.superjob.ru/vacancy/search/?keywords={name}'

    client = MongoClient('localhost', 27017)

    parser = JobParse(url, client)
    try:
        parser.run()
    except ValueError as err:
        print(err)
        pass