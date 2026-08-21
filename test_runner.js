
const puppeteer = require('puppeteer');
(async () => {
    try {
        const browser = await puppeteer.launch({ headless: 'new' });
        const page = await browser.newPage();
        
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') errors.push(msg.text());
        });
        page.on('pageerror', err => {
            errors.push(err.toString());
        });

        await page.goto('https://meandfree23.github.io/re-collection/', { waitUntil: 'networkidle0', timeout: 30000 });
        
        console.log('--- PAGE LOADED ---');
        console.log('Page errors count:', errors.length);
        if (errors.length > 0) console.log('Errors:', errors);
        
        const btn = await page.;
        if (btn) {
            console.log('Button found. Clicking...');
            await btn.click();
            await new Promise(r => setTimeout(r, 1200));
            console.log('Errors after click:', errors);
            const btnText = await page.evaluate(el => el.innerText, btn);
            console.log('Button text:', btnText);
            
            const cardCount = await page.evaluate(() => document.querySelectorAll('.kinfolk-card').length);
            console.log('Total cards count:', cardCount);
        } else {
            console.log('Button NOT found!');
        }

        await browser.close();
    } catch (e) {
        console.error('Test error:', e);
    }
})();
