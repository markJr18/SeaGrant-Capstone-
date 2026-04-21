import express from 'express';
import axios from 'axios';
import * as cheerio from 'cheerio';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());

app.get('/api/reports', async (req, res) => {
  try {
    const { keyword } = req.query;
    const url = 'https://www.scseagrant.org/publications-search/';
    const { data } = await axios.get(url);
    const $ = cheerio.load(data);
    
    const reports = [];
    
    $('table tbody tr').each((i, el) => {
      const titleLink = $(el).find('td:nth-child(1) a');
      const title = titleLink.text().trim();
      const fullUrl = titleLink.attr('href');
      const summary = $(el).find('td:nth-child(2)').text().trim();
      const date = $(el).find('td:nth-child(3)').text().trim();
      const type = $(el).find('td:nth-child(4)').text().trim();
      const topics = $(el).find('td:nth-child(5)').text().trim();
      
      if (title) {
        reports.push({
          id: i,
          title,
          summary,
          date,
          type,
          topics,
          fullUrl: fullUrl ? (fullUrl.startsWith('http') ? fullUrl : `https://www.scseagrant.org${fullUrl}`) : url
        });
      }
    });

    const filteredReports = keyword 
      ? reports.filter(r => 
          r.title.toLowerCase().includes(keyword.toLowerCase()) || 
          r.summary.toLowerCase().includes(keyword.toLowerCase()) ||
          r.topics.toLowerCase().includes(keyword.toLowerCase())
        )
      : reports;

    res.json(filteredReports);
  } catch (error) {
    console.error('Error scraping data:', error);
    res.status(500).json({ error: 'Failed to fetch reports' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
