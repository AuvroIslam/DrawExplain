// Renders every slide of graphics.html to docs/graphics/<name>.png (2400x1350).
// Uses the frontend's playwright: node docs/graphics/source/render.mjs [chromium path]
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { chromium } from "../../../frontend/node_modules/playwright/index.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(here, "..");
const names = {
  problem: "01-problem", solution: "02-solution", why: "03-why-it-works", "app-upload": "04-app-upload",
  "app-dijkstra": "05-app-algorithms", "app-scheduling": "06-app-charts", "app-vision": "07-app-how-it-sees",
  thanks: "08-thank-you",
};
const executablePath = process.argv[2];
const browser = await chromium.launch(executablePath ? { executablePath } : {});
const page = await browser.newPage({ viewport: { width: 1700, height: 1000 }, deviceScaleFactor: 1.5 });
await page.goto(pathToFileURL(path.join(here, "graphics.html")).href, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
for (const [id, name] of Object.entries(names)) {
  await page.locator(`#${id}`).screenshot({ path: path.join(out, `${name}.png`) });
  console.log("wrote", `${name}.png`);
}
await browser.close();
