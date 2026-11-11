# Benchmark prompt

Local paths are replaced with placeholders. The placeholders are not part of the task instruction; they identify the game executable and the supplied handoff document.

## K3.1: complete initial prompt

```text
<GAME_EXE> 给我做个这个游戏的修改器  我要求直观的修改器：给出每个人物的属性页面，并可以随意修改对应数值 @<HANDOFF_MD>
```

English equivalent:

> Build a trainer for this game. I require an intuitive trainer: provide an attribute page for every character and allow the corresponding values to be edited freely.

## Hy4: staged prompts

Initial:

```text
<GAME_EXE> 给我做个这个游戏的修改器
```

Follow-up at 16:47:

```text
@<HANDOFF_MD> 这是这个游戏的详细结构，根据它制作修改器
```

Follow-up at 17:18:

```text
我要求更加直观的修改器：给出每个人物的属性页面，并可以随意修改对应数值
```

Follow-up at 17:42:

```text
@image#1 @image#2 你这不对啊，数值对不上啊
```

The two screenshots are not published because they contain game/save context. The agent's final self-correction is preserved in [evidence/hy4/final-response.md](../evidence/hy4/final-response.md).

## K3.1: UI defect follow-up

At 18:37:02, after the first executable was delivered:

```text
当我用修改器修改数值时，会立刻跳变为原先数值，导致修改的数值还没来得及写入就变成原来的值了
```

English equivalent:

> When I edit a value, it immediately jumps back to the original, so the modified value turns back before it can be written.

## Qwen4

The original Qoder conversation prompt was not available with the artifact. The operator supplied the label Qwen4, but this dossier does not invent a prompt for that run. The artifact was evaluated against the same intended product requirement.
