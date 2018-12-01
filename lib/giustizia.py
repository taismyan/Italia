# -*- coding: utf-8 -*-
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from secrets import uuid, devicename, deviceheight, devicewidth, token

query_url = "https://mob1.processotelematico.giustizia.it/proxy/index_mobile.php"
base_payload = dict(
    version="1.1.13",
    platform="iOS 12.1",
    uuid=uuid,
    devicename=devicename,
    devicewidth=devicewidth,
    deviceheight=deviceheight,
    token=token,
    azione="direttarg_sicid_mobile",
    registro="CC",
    idufficio="0580910098",
    tipoufficio=1
)

inscrito_ruolo_re = re.compile("\<li\>iscritto al ruolo il (.+)\<\/li\>")
remove_lawyer_prefix = re.compile("(?<=Avv. ).*")


class Case:
    def __init__(self, case_yr, case_no, date_filed, judge_name, date_hearing, case_state, primary_lawyer_initials):
        self.year = case_yr
        self.number = case_no
        self.date_filed = date_filed
        self.date_hearing = date_hearing
        self.judge_name = judge_name
        self.case_state = case_state
        self.primary_lawyer_initials = primary_lawyer_initials

    def __str__(self):
        return ";".join([
            '{}/{}'.format(self.number, self.year),
            self.date_filed,
            self.judge_name,
            self.date_hearing,
            self.case_state,
            self.primary_lawyer_initials,
        ])

    def asdict(self):
        return {
            'case_yr': self.year,
            'case_no': self.number,
            'date_filed': self.date_filed,
            'date_hearing': self.date_hearing,
            'judge_name': self.judge_name,
            'case_state': self.case_state,
            'primary_lawyer_initials': self.primary_lawyer_initials,
        }


def get_case_details(case_yr, case_no):
    payload = base_payload.copy()

    payload.update(dict(
        aaproc=str(case_yr),
        numproc=str(case_no),
        _=int(datetime.now().timestamp())  # este parâmetro é o tipespam, tem que ser diferente para cada request
    ))

    response = requests.get(query_url, params=payload)
    content = response.text

    if "cittadinanza" in content:

        bs = BeautifulSoup(content)
        nome_giudice = bs.find("nomegiudice")
        data_udienza = bs.find("dataudienza")

        inscrito_ruolo_search = inscrito_ruolo_re.search(content)
        if inscrito_ruolo_search:
            data_inscricao = inscrito_ruolo_search.groups()[0]
        else:
            data_inscricao = "???"

        case_state = extract_case_state_from_content(bs) or "Unknown"

        nome_giudice = nome_giudice.string if nome_giudice else "Not Assigned"
        data_udienza = data_udienza.string[:10] if data_udienza else "Not Assigned"

        primary_lawyer_initials = extract_primary_lawyer_initials(bs) or "Unknown"

        return Case(
            case_yr,
            case_no,
            data_inscricao,
            nome_giudice,
            data_udienza,
            case_state,
            primary_lawyer_initials
        )


def extract_case_state_from_content(bs_content):
    try:
        case_state_list_copy = bs_content.findAll("li")
        for idx, val in enumerate(case_state_list_copy):
            if val.contents[0] == 'Stato fascicolo':
                return case_state_list_copy[idx + 1].contents[0]
        return None
    except:
        return None


def extract_primary_lawyer_initials(bs_content):
    try:
        case_state_list_copy = bs_content.findAll("li")
        for idx, val in enumerate(case_state_list_copy):
            if val.contents[0] == 'Parti fascicolo':
                redacted_name = remove_lawyer_prefix.search(case_state_list_copy[idx + 1].contents[3]).group(0)
                return redacted_name.replace(' ', '').replace('*', '')
        return None
    except:
        return None
