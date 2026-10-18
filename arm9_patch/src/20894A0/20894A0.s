@ 字符显示宽度
ldrh r1, [sp, #0x28]
mov r0, #12
mul r1, r0, r1
cmp r1, #72
movle r8, #2
ble 0x020894CC
cmp r1, #135
movle r8, #1
