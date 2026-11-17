package main

import (
	"strings"
	"testing"

	"github.com/google/uuid"
)

func TestUUIDString(t *testing.T) {
	id := uuid.NewString()
	if len(id) != 36 || strings.Count(id, "-") != 4 {
		t.Fatalf("UUID 格式不对: %q", id)
	}
	if _, err := uuid.Parse(id); err != nil {
		t.Fatalf("Parse 失败: %v", err)
	}
}

func TestUUIDVersion(t *testing.T) {
	id := uuid.New()
	if id.Version() != 4 {
		t.Fatalf("期望 v4 UUID，实际 %d", id.Version())
	}
}
