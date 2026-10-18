@ Load the lower-screen credits after the original VRAM clear.
push {r1-r5, lr}
ldr r0, =BootCreditsBackground
ldr r1, =0x6200000
ldr r3, =0x20905A8
blx r3
ldr r0, =BootCreditsPalette
ldr r1, =0x5000400
mov r2, #32
ldr r3, =0x20903DC
blx r3
ldr r1, =0x4001008
mov r0, #0x1000
strh r0, [r1]
mov r0, #0
str r0, [r1, #8]
sub r1, r1, #8
ldr r0, =0x10100
str r0, [r1]
ldr r0, =0x215B25C
pop {r1-r5, pc}
.ltorg

.org 0x80
@ Disable the credits background after the original screen shutdown.
push {r0-r2, lr}
ldr r3, =0x2013DDC
blx r3
ldr r1, =0x4001000
mov r0, #0
str r0, [r1]
pop {r0-r2, pc}
.ltorg

BootCreditsPalette:
.incbin "../../temp/import/boot_credits/boot_credits.pal"
.balign 4
BootCreditsBackground:
.incbin "../../temp/import/boot_credits/boot_credits.lz"
.balign 4
