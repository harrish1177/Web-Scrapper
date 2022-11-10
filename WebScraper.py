"""
Created by Harrish Kumar S
email - harrish1177@gmail.com
Note - https://www.gov.uk/contracts-finder - This website is used and Tender details in this website are scraped
November 2022
"""

import requests
from bs4 import BeautifulSoup
import re
from csv import DictWriter
import datetime
import pandas as pd
from matplotlib import pyplot as plt


class Tender:
    """ TENDER FILE NAME """
    FILE_NAME = "Tender.csv"

    """ TENDER INFO KEYS"""
    TITLE = "Tender Title"
    ORGANIZATION = "Organization"
    DESCRIPTION = "Description"

    """ TENDER META DATA KEYS"""
    PROCUREMENT_STAGE = "Procurement stage"
    NOTICE_STATUS = "Notice status"
    APPROACH_TO_MARKET_DATE = "Approach to market date"
    CLOSING = "Closing"
    CONTRACT_LOCATION = "Contract location"
    CONTRACT_VALUE = "Contract value"
    MIN_CONTRACT_VALUE = "Min Contract value"
    MAX_CONTRACT_VALUE = "Max Contract value"
    PUBLICATION_DATE = "Publication date"
    LAST_EDITED = "Last Edited"

    """ CLASS VARIABLES """
    SOUP = None
    SCRAP_OBJ = None
    TOTAL_PAGES = 1
    REQUEST = None
    NOT_AVAILABLE = "Not Available"

    """ CSV Key List """
    CSV_KEY = [
           TITLE,
           ORGANIZATION,
           DESCRIPTION,
           PROCUREMENT_STAGE,
           NOTICE_STATUS,
           APPROACH_TO_MARKET_DATE,
           CLOSING,
           CONTRACT_LOCATION,
           MIN_CONTRACT_VALUE,
           MAX_CONTRACT_VALUE,
           PUBLICATION_DATE,
           LAST_EDITED
            ]

    """ MONEY RANGE VALUES """
    ZER0_TO_10K          = '0 to 10k'
    TEN_TO_50K           = '10 to 50k'
    FIFTY_K_TO_100K      = '50k to 100k'
    HUNDRED_K_TO_500K    = '100k to 500k'
    FIVE_HUNDRED_K_TO_1M = '500k to 1M'
    ONE_M_TO_5_M         = '1M to 5M'
    GREATER_THAN_5M      = ' >5M'

    money_range = {
        ZER0_TO_10K             : 0,
        TEN_TO_50K              : 0,
        FIFTY_K_TO_100K         : 0,
        HUNDRED_K_TO_500K       : 0,
        FIVE_HUNDRED_K_TO_1M    : 0,
        ONE_M_TO_5_M            : 0,
        GREATER_THAN_5M         : 0
    }

    def __init__(self, tender_info):
        self.title = tender_info.find('div', class_="search-result-header").get('title')
        self.organization = tender_info.find('div', class_="search-result-sub-header").text
        self.description = tender_info.find_all('div', class_="wrap-text")[1].text
        self.meta_data_values_grep = tender_info.find_all('div', class_="search-result-entry")
        self.meta_data = dict()
        # store meta data in a dictionary
        for data in self.meta_data_values_grep:
            key = data.find('strong').text
            val = data.text.replace(key, "").strip()
            if Tender.CONTRACT_VALUE in key:
                if 'to' in val:
                    minval , maxval = val.split('to')
                    minval = minval.replace('£', "").replace(",","").strip()
                    maxval = maxval.replace('£', "").replace(",","").strip()
                    self.meta_data[Tender.MIN_CONTRACT_VALUE] = minval
                    self.meta_data[Tender.MAX_CONTRACT_VALUE] = maxval

                else:
                    self.meta_data[Tender.MIN_CONTRACT_VALUE] = val.replace('£', "").replace(',','').strip()
                    self.meta_data[Tender.MAX_CONTRACT_VALUE] = Tender.NOT_AVAILABLE
                continue

            self.meta_data[key] = val

            if Tender.PUBLICATION_DATE in key:
                if ',' in val:
                    self.meta_data[Tender.LAST_EDITED] = re.findall(r'[0-9].*',val.split(",")[-1])[0]
                    self.meta_data[key] = val.split(",")[0]
                else:
                    self.meta_data[Tender.LAST_EDITED] = Tender.NOT_AVAILABLE


    # make HTTP request
    @classmethod
    def make_request(cls, page_no):
        r = requests.get(f'https://www.contractsfinder.service.gov.uk/Search/Results?&page={page_no}#dashboard_notices')
        Tender.REQUEST = r if r.status_code == 200 else None
        return Tender.REQUEST

    # get the soup object
    @classmethod
    def get_soup(cls):
        soup = BeautifulSoup(Tender.REQUEST.content, 'html.parser')
        Tender.SOUP = soup
        return Tender.SOUP

    # Scrap and find the relevant search results of tender details
    @classmethod
    def get_scrap_obj(cls, page_no):
        cls.make_request(page_no)
        cls.get_soup()
        Tender.SCRAP_OBJ = Tender.SOUP.find_all('div', class_='search-result')
        return Tender.SCRAP_OBJ

    # Get the total no.of.pages to be scraped
    @classmethod
    def get_total_pages(cls):
        cls.get_scrap_obj(1)
        gadget_footer = Tender.SOUP.find(class_="gadget-footer")
        ul = gadget_footer.find('ul', class_="gadget-footer-paginate")
        content = ul.find_all('li')[-1].text
        total_pages = re.findall(r'[0-9]+', content)[-1]
        cls.TOTAL_PAGES = int(total_pages)
        return cls.TOTAL_PAGES

    # Scrap each webpage of search results, find the tender details and enter into the csv file
    @classmethod
    def create_rows(cls, rows):
        with open(cls.FILE_NAME, 'a', newline='', encoding="utf-8") as fobj:
            dictwriter_object = DictWriter(fobj, fieldnames= cls.CSV_KEY, restval = Tender.NOT_AVAILABLE)
            dictwriter_object.writerows(rows)

    # pre-process the tender data to be entered into the csv file
    @classmethod
    def write_csv(cls, All_tenders_in_page):
        rows = []
        for tender in All_tenders_in_page:
            csv_row_dict = dict()
            csv_row_dict[tender.TITLE] = tender.title
            csv_row_dict[tender.ORGANIZATION] = tender.organization
            csv_row_dict[tender.DESCRIPTION] = tender.description
            # Update csv_row_dict with tender metadata
            csv_row_dict.update(tender.meta_data)
            rows.append(csv_row_dict.copy())
        cls.create_rows(rows)

    # Enter the first row representing column names
    @classmethod
    def create_col_heading(cls):
        with open(cls.FILE_NAME, 'a', newline='', encoding="utf-8") as fobj:
            dictwriter_object = DictWriter(fobj, fieldnames= cls.CSV_KEY, restval = "Not Available")
            dictwriter_object.writeheader()

    # Get the string value as integer. If garbage or undesired value is found, return 0
    @classmethod
    def get_val_as_int(cls, val):
        try:
            res = int(val)
            return res
        except:
            return 0

    # read the csv file and find the total tenders falling in each Contract money range
    @classmethod
    def get_data_from_csv_for_contract_value(cls):
        data = pd.read_csv(cls.FILE_NAME)
        contract_value = data[cls.MIN_CONTRACT_VALUE].tolist()

        for val in contract_value:
            val = cls.get_val_as_int(val)
            if val >= 0 and val <= 10_000:
                cls.money_range[cls.ZER0_TO_10K] += 1
            elif val > 10_000 and val <= 50_000:
                cls.money_range[cls.TEN_TO_50K] += 1
            elif val > 50_000 and val <= 100_000:
                cls.money_range[cls.FIFTY_K_TO_100K] += 1
            elif val > 100_000 and val <= 500_000:
                cls.money_range[cls.HUNDRED_K_TO_500K] += 1
            elif val > 500_000 and val <= 10_00_000:
                cls.money_range[cls.FIVE_HUNDRED_K_TO_1M] += 1
            elif val > 10_00_000 and val <= 50_00_000:
                cls.money_range[cls.ONE_M_TO_5_M] += 1
            else:
                cls.money_range[cls.GREATER_THAN_5M] += 1

    # Display tender Contract value as a Bar graph
    @classmethod
    def show_tender_contract_value_graph(cls):
        cls.get_data_from_csv_for_contract_value()
        money_range_x_axis = cls.money_range.keys()
        tender_count_y_axis = cls.money_range.values()
        plt.figure(figsize=(11, 5))

        plt.bar(money_range_x_axis, tender_count_y_axis, color='red',
                width=0.4)

        plt.xlabel("Contract Money Range")
        plt.ylabel("Tender Count")
        plt.title("Total Tenders in various Contract Money Ranges")
        plt.show()

    # Read the csv file and find the total tenders filed in each month of 2022 till November
    @classmethod
    def get_monthly_data_from_csv(cls):
        data = pd.read_csv(cls.FILE_NAME)
        csv_date_list = data[cls.PUBLICATION_DATE].tolist()
        month_tender_list = [0]*12
        date_format = "%d %B %Y"
        for eachdate in csv_date_list:
            if eachdate != cls.NOT_AVAILABLE:
                date_obj = datetime.datetime.strptime(eachdate, date_format)
                if date_obj.year == 2022:
                    month_tender_list[date_obj.month - 1] += 1
        # Till November because, the script is written in November. Total tenders on December by then is 0
        month_tender_dict = {
            'January'   : month_tender_list[0],
            'February'  : month_tender_list[1],
            'March'     : month_tender_list[2],
            'April'     : month_tender_list[3],
            'May'       : month_tender_list[4],
            'June'      : month_tender_list[5],
            'July'      : month_tender_list[6],
            'August'    : month_tender_list[7],
            'September' : month_tender_list[8],
            'October'   : month_tender_list[9],
            'November'  : month_tender_list[10],
        }
        return month_tender_dict

    # Display the total tenders filed in each month of year 2022 as a bar graph
    @classmethod
    def show_total_tenders_in_each_month(cls):
        month_tender_dict = cls.get_monthly_data_from_csv()
        month_x_axis = month_tender_dict.keys()
        total_tender_y_axis = month_tender_dict.values()
        plt.figure(figsize=(11, 5))
        plt.bar(month_x_axis, total_tender_y_axis, color='green',
                width=0.4)

        plt.xlabel("---Months---")
        plt.ylabel("Tender Count")
        plt.title("Tenders filed in the months of year 2022")
        plt.show()

    # Global API users can use to get the tender details in a csv file
    @classmethod
    def get_csv(cls):
        cls.get_total_pages()
        cls.create_col_heading()
        for pageno in range(1, Tender.TOTAL_PAGES+1):
            cls.get_scrap_obj(pageno)
            print(f"Scraping Page {pageno} of {cls.TOTAL_PAGES}")
            All_tenders_in_page = []
            for tender_info in Tender.SCRAP_OBJ:
                All_tenders_in_page.append(Tender(tender_info))
            cls.write_csv(All_tenders_in_page)

    # String representation of Tender details (Object)
    def __str__(self):
        string = ""
        string += "\nPrinting Tender Object"
        string += f"\nTitle : {self.title}"
        string += f"\nOrganization : {self.organization}"
        string += f"\nDescription : {self.description}"
        for key, val in self.meta_data.items():
            string += f"\n{key} : {val}"
        return string


"""
Tender.get_csv() -> Use this to get the tender details in a  Tender.csv file
Tender.show_tender_contract_value_graph() -> Use this to visualize the count of tenders falling in various money ranges
Tender.show_total_tenders_in_each_month() -> Use this to visualize the count of tenders found in every month in year 2022
"""

if __name__ == '__main__':
    try:
        # Tender.get_csv() -> Use this to get the tender details in a  Tender.csv file
        Tender.get_csv()
        # Tender.show_tender_contract_value_graph() -> Use this to visualize the count of tenders falling in various money ranges
        Tender.show_tender_contract_value_graph()
        # Tender.show_total_tenders_in_each_month() -> Use this to visualize the count of tenders found in every month in year 2022
        Tender.show_total_tenders_in_each_month()
        pass
    except:
        print("Some issue found")