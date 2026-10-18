@ 使用职员表的原始字形
push {r0, r1, r3, lr}
ldrb r2, [r2]
cmp r0, #0
beq 3f
ldr r1, [r0, #0x14]
ldr r3, =0x20E8A54
cmp r1, r3
blo 3f
ldr r3, =0x20E92D4
cmp r1, r3
orrlo r2, r2, #0x100
3:
pop {r0, r1, r3, pc}
.ltorg

.org 0xc0
@ 字符间距
ldr r1, [sp]
tst r1, #0x100
ldrneb r1, [r4, #0x15]
moveq r1, #12
bx lr

.org 0xe0
@ 原始字形紧跟在 12x12 字形之后
tst r8, #0x100
addne r0, r0, #38
mov r6, r0
bx lr

.org 0x110
tst r8, #0x100
mov r0, #3
movne r0, #2
bx lr

.org 0x120
tst r8, #0x100
mov r0, #12
movne r0, #16
bx lr

.org 0x130
tst r8, #0x100
mov r0, #12
movne r0, #8
bx lr
