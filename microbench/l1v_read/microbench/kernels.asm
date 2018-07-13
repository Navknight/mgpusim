.hsa_code_object_version 2,1
.hsa_code_object_isa 8,0,3,"AMD","AMDGPU"

.text
.p2align        8
.amdgpu_hsa_kernel microbench
		
microbench:                             ; @microbench

.amd_kernel_code_t
kernarg_segment_byte_size = 32
wavefront_sgpr_count = 8
workitem_vgpr_count = 5
.end_amd_kernel_code_t

BB0_0:
	s_load_dwordx2 s[6:7], s[4:5], 0x0
	s_load_dword s8, s[4:5], 0x8
	s_mov_b32 s1, 0
	v_mov_b32 v1, s6
	v_mov_b32 v2, s7

BB0_1:
	flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)
flat_load_dword v0, v[1:2]
s_waitcnt vmcnt(0)


BB0_5:
	s_endpgm

