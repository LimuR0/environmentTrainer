package com.example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.apache.commons.lang3.JavaVersion;
import org.apache.commons.lang3.SystemUtils;
import org.junit.jupiter.api.Test;

class AppTest {

    @Test
    void shoutWorks() {
        assertEquals("Env Demo!", App.shout("  env demo  "));
    }

    @Test
    void commonsLangIsRecent() {
        // 3.13 之前没有 JavaVersion 的这套判断（这里只是顺带证明拿到的是新版本）
        assertTrue(SystemUtils.isJavaVersionAtLeast(JavaVersion.JAVA_17));
    }
}
