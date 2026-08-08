import { CheckIcon, PlusIcon, UserRoundPenIcon, XIcon } from "lucide-react"
import { type FormEvent, type SVGProps, useId, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Textarea } from "@/components/ui/textarea"
import type { DiamondEntity } from "@/features/intelligence/intelligence-types"
import { cn } from "@/lib/utils"

export type ReviewEntity = DiamondEntity & {
  id: string
  included: boolean
  origin: "auto" | "analyst"
}

type IconComponent = (props: SVGProps<SVGSVGElement>) => React.ReactNode

export function EntityReviewCard({
  title,
  description,
  icon: Icon,
  entities,
  defaultType,
  readOnly,
  onChange,
}: {
  title: string
  description: string
  icon: IconComponent
  entities: ReviewEntity[]
  defaultType: string
  readOnly: boolean
  onChange: (entities: ReviewEntity[]) => void
}) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [name, setName] = useState("")
  const [entityType, setEntityType] = useState(defaultType)
  const [confidence, setConfidence] = useState("80")
  const [evidence, setEvidence] = useState("")
  const fieldId = useId()
  const parsedConfidence = Number(confidence)
  const canAdd =
    name.trim().length > 0 &&
    entityType.trim().length > 0 &&
    Number.isInteger(parsedConfidence) &&
    parsedConfidence >= 0 &&
    parsedConfidence <= 100

  function addEntity(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canAdd) return
    onChange([
      ...entities,
      {
        id: `analyst-${Date.now()}-${name.trim()}`,
        name: name.trim(),
        type: entityType.trim(),
        confidence: parsedConfidence,
        evidence: evidence.trim(),
        included: true,
        origin: "analyst",
      },
    ])
    setName("")
    setEntityType(defaultType)
    setConfidence("80")
    setEvidence("")
    setDialogOpen(false)
  }

  function setIncluded(id: string, included: boolean) {
    onChange(
      entities.map((entity) =>
        entity.id === id ? { ...entity, included } : entity
      )
    )
  }

  return (
    <Card className="min-w-0 gap-3 py-4">
      <CardHeader className="px-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-primary">
              <Icon aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <CardTitle className="text-sm">{title}</CardTitle>
              <CardDescription>{description}</CardDescription>
            </div>
          </div>
          {!readOnly && (
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  aria-label={`添加${title}实体`}
                  size="icon-sm"
                  variant="ghost"
                >
                  <PlusIcon />
                </Button>
              </DialogTrigger>
              <DialogContent>
                <form className="contents" onSubmit={addEntity}>
                  <DialogHeader>
                    <DialogTitle>添加{title}实体</DialogTitle>
                    <DialogDescription>
                      手动补充的字段会标记为分析员输入，并写入审核快照。
                    </DialogDescription>
                  </DialogHeader>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor={`${fieldId}-name`}>名称</FieldLabel>
                      <Input
                        autoFocus
                        id={`${fieldId}-name`}
                        maxLength={500}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="例如：Midnight Blizzard"
                        value={name}
                      />
                    </Field>
                    <div className="grid grid-cols-2 gap-3">
                      <Field>
                        <FieldLabel htmlFor={`${fieldId}-type`}>
                          实体类型
                        </FieldLabel>
                        <Input
                          id={`${fieldId}-type`}
                          maxLength={100}
                          onChange={(event) =>
                            setEntityType(event.target.value)
                          }
                          value={entityType}
                        />
                      </Field>
                      <Field>
                        <FieldLabel htmlFor={`${fieldId}-confidence`}>
                          置信度
                        </FieldLabel>
                        <Input
                          id={`${fieldId}-confidence`}
                          inputMode="numeric"
                          max={100}
                          min={0}
                          onChange={(event) =>
                            setConfidence(event.target.value)
                          }
                          type="number"
                          value={confidence}
                        />
                      </Field>
                    </div>
                    <Field>
                      <FieldLabel htmlFor={`${fieldId}-evidence`}>
                        证据说明
                      </FieldLabel>
                      <Textarea
                        id={`${fieldId}-evidence`}
                        maxLength={5000}
                        onChange={(event) => setEvidence(event.target.value)}
                        placeholder="粘贴原文摘录或记录分析依据…"
                        rows={3}
                        value={evidence}
                      />
                    </Field>
                  </FieldGroup>
                  <DialogFooter showCloseButton>
                    <Button disabled={!canAdd} type="submit">
                      <PlusIcon data-icon="inline-start" />
                      添加实体
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 px-4">
        {entities.length ? (
          entities.map((entity) => (
            <div
              className={cn(
                "rounded-md border border-border bg-background/45 p-3 transition-opacity",
                !entity.included && "opacity-45"
              )}
              key={entity.id}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="min-w-0 truncate text-sm font-medium">
                      {entity.name}
                    </span>
                    {entity.origin === "analyst" && (
                      <Badge variant="secondary">
                        <UserRoundPenIcon data-icon="inline-start" />
                        人工
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {entity.type} · {entity.confidence}%
                  </p>
                </div>
                {!readOnly && (
                  <ToggleGroup
                    aria-label={`${entity.name}审核状态`}
                    onValueChange={(value) => {
                      if (value) setIncluded(entity.id, value === "keep")
                    }}
                    size="sm"
                    spacing={0}
                    type="single"
                    value={entity.included ? "keep" : "exclude"}
                    variant="outline"
                  >
                    <ToggleGroupItem
                      aria-label={`保留 ${entity.name}`}
                      value="keep"
                    >
                      <CheckIcon />
                    </ToggleGroupItem>
                    <ToggleGroupItem
                      aria-label={`排除 ${entity.name}`}
                      value="exclude"
                    >
                      <XIcon />
                    </ToggleGroupItem>
                  </ToggleGroup>
                )}
              </div>
              {entity.evidence && (
                <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">
                  {entity.evidence}
                </p>
              )}
            </div>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
            未从正文中提取到，可由分析员手动补充。
          </p>
        )}
      </CardContent>
    </Card>
  )
}
