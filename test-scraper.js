import axios from 'axios';
import * as cheerio from 'cheerio';

async function testScraper() {
  try {
    const url = 'https://www.scseagrant.org/publications-search/';
    const { data } = await axios.get(url);
    const $ = cheerio.load(data);
    
    console.log('Table rows found:', $('table tbody tr').length);
    
    $('table tbody tr').slice(0, 5).each((i, el) => {
      const title = $(el).find('td:nth-child(1) a').text().trim();
      const fullUrl = $(el).find('td:nth-child(1) a').attr('href');
      console.log(`Row ${i}:`, { title, fullUrl });
    });
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testScraper();
