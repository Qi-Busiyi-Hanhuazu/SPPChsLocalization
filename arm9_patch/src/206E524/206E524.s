@ 字符 bpp
ldr r0, [sp]
tst r8, #0x100
addeq r0, r0, #2
str r0, [sp]
mov r5, #2
