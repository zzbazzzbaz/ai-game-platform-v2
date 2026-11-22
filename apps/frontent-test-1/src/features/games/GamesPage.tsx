import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Gamepad2, LoaderCircle, Plus, RefreshCw } from "lucide-react";
import { Link } from "react-router";

import { listGames, type GameResponse } from "@/api/games";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { NewGameDialog } from "@/features/games/NewGameDialog";
import { formatDateTime } from "@/lib/format";

const DEMO_NAME_SUFFIX = " · 体验版";

function GameCard({ game }: { game: GameResponse }) {
  const published = game.public_url !== null;
  const isDemo = game.name.endsWith(DEMO_NAME_SUFFIX);

  return (
    <Card className="gap-4 py-5 transition-shadow hover:shadow-md">
      <CardHeader className="gap-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="truncate text-base">{game.name}</CardTitle>
          <div className="flex shrink-0 flex-wrap justify-end gap-1">
            {isDemo && <Badge variant="outline">体验版</Badge>}
            {published ? (
              <Badge variant="success">已发布</Badge>
            ) : (
              <Badge variant="secondary">未发布</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="text-muted-foreground flex flex-col gap-1 text-xs">
        <span>创建于 {formatDateTime(game.created_at)}</span>
        <span>最后活动 {formatDateTime(game.updated_at ?? game.created_at)}</span>
      </CardContent>
      <CardFooter className="gap-2">
        <Button asChild size="sm" className="flex-1">
          <Link to={`/games/${game.game_id}`}>进入</Link>
        </Button>
        {game.public_url !== null && (
          <Button asChild size="sm" variant="outline">
            <a href={game.public_url} target="_blank" rel="noreferrer">
              <ExternalLink />
              打开游戏
            </a>
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

function GamesSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, index) => (
        <Card key={index} className="gap-4 py-5">
          <CardHeader>
            <Skeleton className="h-5 w-1/2" />
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </CardContent>
          <CardFooter>
            <Skeleton className="h-8 w-full" />
          </CardFooter>
        </Card>
      ))}
    </div>
  );
}

export function GamesPage() {
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const { data, isPending, isError, error, refetch, isRefetching } = useQuery({
    queryKey: ["games"],
    queryFn: listGames,
  });

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">我的游戏</h1>
          <p className="text-muted-foreground text-sm">选择一个游戏继续，或创建一个新的</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus />
          新建游戏
        </Button>
      </div>

      {isPending ? (
        <GamesSkeleton />
      ) : isError ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed p-10 text-center">
          <p className="text-destructive text-sm">{error.message}</p>
          <Button variant="outline" onClick={() => void refetch()} disabled={isRefetching}>
            {isRefetching ? <LoaderCircle className="animate-spin" /> : <RefreshCw />}
            重试
          </Button>
        </div>
      ) : data.length === 0 ? (
        <div className="flex flex-col items-center gap-4 rounded-lg border border-dashed p-12 text-center">
          <span className="bg-muted flex size-12 items-center justify-center rounded-full">
            <Gamepad2 className="size-6" />
          </span>
          <div>
            <p className="font-medium">还没有游戏</p>
            <p className="text-muted-foreground text-sm">
              创建后与 AI 对话，描述你想玩的游戏
            </p>
          </div>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus />
            创建第一个游戏
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((game) => (
            <GameCard key={game.game_id} game={game} />
          ))}
        </div>
      )}

      <NewGameDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}
