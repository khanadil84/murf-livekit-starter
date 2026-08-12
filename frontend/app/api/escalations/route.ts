import { NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET() {
  try {
    const filePath = path.join(
      process.cwd(),
      "..",
      "backend",
      "escalations.json"
    );

    try {
      const file = await fs.readFile(filePath, "utf-8");
      const data = JSON.parse(file);

      return NextResponse.json(data);
    } catch {
      return NextResponse.json([]);
    }
  } catch (error) {
    console.error("Failed to load escalations:", error);

    return NextResponse.json(
      { error: "Failed to load escalation requests" },
      { status: 500 }
    );
  }
}