import GameView from "@/components/GameView";

export default async function GamePage({
  params,
  searchParams,
}: {
  params: Promise<{ appid: string }>;
  searchParams: Promise<{ rank?: string; because?: string; flags?: string }>;
}) {
  const { appid } = await params;
  const sp = await searchParams;
  const why = sp.rank
    ? { rank: Number(sp.rank), because: sp.because ? sp.because.split("|") : [], flags: sp.flags ? sp.flags.split(",") : [] }
    : null;
  return <GameView appId={Number(appid)} why={why} />;
}
