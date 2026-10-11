import { Link } from "react-router";

import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-4xl font-semibold">404</p>
        <p className="text-muted-foreground text-sm">页面不存在或已被移除</p>
        <Button asChild variant="outline">
          <Link to="/">返回首页</Link>
        </Button>
      </div>
    </div>
  );
}
