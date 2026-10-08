const express = require("express");
const { Pool } = require("pg");

const app = express();
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: false,
});

app.get("/", (req, res) => {
  res.json({
    ok: true,
    service: "api-deploy-probe",
    gameId: process.env.GAME_ID || null,
    time: new Date().toISOString(),
  });
});

app.get("/db", async (req, res) => {
  try {
    const r = await pool.query(
      "select current_database() as db, current_user as usr, version() as v"
    );
    res.json({
      ok: true,
      db: r.rows[0].db,
      user: r.rows[0].usr,
      version: r.rows[0].v.slice(0, 48),
    });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
});

const port = Number(process.env.PORT || 3000);
app.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
