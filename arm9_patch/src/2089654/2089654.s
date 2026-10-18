@ 字符显示宽度
ldrsh r5, [sp, #0x2E]
ldrh r4, [sp, #0x28]
add r5, r5, r5, lsl #3
mov r0, #12
mul r4, r0, r4
mov r0, #0x10000000
mov r1, r5
bl 0x020063C4
mul r1, r0, r4
mov r0, r1, lsr #16
str r0, [r6, #0xC]
ldr r1, [r7, #0x98]
sub r2, r5, r4
mov r0, r1, asr #16
mov r1, r2, asr #1
add r0, r0, r1
mov r0, r0, lsl #16
str r0, [r7, #0x98]
b 0x02089700
