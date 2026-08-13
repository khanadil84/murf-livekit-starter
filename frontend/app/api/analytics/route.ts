import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET() {
  try {
    const analyticsPath = path.join(
      process.cwd(),
      "..",
      "backend",
      "analytics.json"
    );

    const file = await fs.readFile(analyticsPath, "utf-8");
    const data = JSON.parse(file);

    return NextResponse.json(data, {
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    console.error("Failed to read call analytics:", error);

    return NextResponse.json(
      { error: "Unable to load call analytics" },
      { status: 500 }
    );
  }
}