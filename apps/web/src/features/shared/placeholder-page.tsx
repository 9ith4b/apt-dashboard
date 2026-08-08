import { ConstructionIcon } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function PlaceholderPage({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <span className="mb-2 flex size-10 items-center justify-center rounded-lg bg-secondary text-primary">
            <ConstructionIcon aria-hidden="true" />
          </span>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          当前路由和应用外壳已经建立，后续里程碑会在此处接入真实领域数据和交互。
        </CardContent>
      </Card>
    </div>
  )
}
