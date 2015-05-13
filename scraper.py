from urlparse import urljoin
import requests
import lxml.html

source_url = 'http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479'
resp = requests.get(source_url)

root = lxml.html.fromstring(resp.text)

terms = [(x.find('span').text.strip(), urljoin(source_url, x.get('href')))
         for x in root.cssselect('.menu-treemenu')[0].cssselect('a')]

data = []

for term_name, term_url in terms:

    while term_url:
        print term_url
        term_resp = requests.get(term_url)
        term_root = lxml.html.fromstring(term_resp.text)

        next_links = term_root.cssselect('a[title=Next]')
        term_url = urljoin(term_url, next_links[0].get('href')) if next_links else None

# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".
