package insts_test

import (
	. "github.com/onsi/ginkgo"
	. "github.com/onsi/gomega"
	"gitlab.com/akita/mgpusim/insts"
)

var _ = Describe("Register", func() {
	It("should get correct v register", func() {
		Expect(insts.VReg(0)).To(BeIdenticalTo(insts.Regs[insts.V0]))
		Expect(insts.VReg(5)).To(BeIdenticalTo(insts.Regs[insts.V5]))
	})

	It("should get correct s register", func() {
		Expect(insts.SReg(0)).To(BeIdenticalTo(insts.Regs[insts.S0]))
		Expect(insts.SReg(5)).To(BeIdenticalTo(insts.Regs[insts.S5]))
	})

})
