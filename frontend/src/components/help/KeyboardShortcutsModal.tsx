/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * KeyboardShortcutsModal — cheatsheet of all in-app shortcuts.
 *
 * Opened by pressing "?" anywhere in the app (except in inputs), or from the
 * user-menu "Keyboard Shortcuts" entry.
 */

import React from 'react';
import { Modal, Typography, Space, Tag, Divider } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface Shortcut {
  keys: string[];
  description: string;
  /** Optional target context (e.g. "on Help button") shown after the description. */
  target?: string;
}

interface ShortcutSection {
  title: string;
  shortcuts: Shortcut[];
}

const isMac =
  typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/i.test(navigator.platform);
const cmd = isMac ? '⌘' : 'Ctrl';

const SECTIONS: ShortcutSection[] = [
  {
    title: 'Global',
    shortcuts: [
      { keys: [cmd, 'K'], description: 'Open command palette' },
      { keys: ['?'], description: 'Show this shortcuts dialog' },
      { keys: ['Shift', 'Click'], description: 'Open full help page', target: 'on header help icon' },
    ],
  },
  {
    title: 'Scenario Studio',
    shortcuts: [
      { keys: [cmd, 'S'], description: 'Save explicit version snapshot' },
      { keys: [cmd, 'D'], description: 'Duplicate selected device' },
      { keys: [cmd, 'A'], description: 'Select all devices' },
      { keys: ['G'], description: 'Cycle canvas group-by mode' },
      { keys: ['Esc'], description: 'Close context menu / clear selection' },
    ],
  },
  {
    title: 'AI Chat',
    shortcuts: [
      { keys: [cmd, 'Enter'], description: 'Send message', target: 'in AI chat input' },
    ],
  },
];

const KeyTag: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Tag
    style={{
      background: '#1a1a2e',
      border: '1px solid #2d2d52',
      color: '#e0e8f0',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      fontSize: 12,
      padding: '2px 8px',
      margin: 0,
    }}
  >
    {children}
  </Tag>
);

const ShortcutRow: React.FC<{ shortcut: Shortcut }> = ({ shortcut }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 0',
    }}
  >
    <div style={{ flex: 1 }}>
      <Text style={{ color: '#e0e8f0' }}>{shortcut.description}</Text>
      {shortcut.target && (
        <Text style={{ color: '#6b6b8a', fontSize: 11, marginLeft: 8 }}>
          {shortcut.target}
        </Text>
      )}
    </div>
    <Space size={4}>
      {shortcut.keys.map((key, i) => (
        <React.Fragment key={i}>
          {i > 0 && <Text style={{ color: '#6b6b8a' }}>+</Text>}
          <KeyTag>{key}</KeyTag>
        </React.Fragment>
      ))}
    </Space>
  </div>
);

interface KeyboardShortcutsModalProps {
  open: boolean;
  onClose: () => void;
}

const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({ open, onClose }) => {
  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#049FD9' }} />
          <span>Keyboard Shortcuts</span>
        </Space>
      }
      styles={{
        content: { background: '#0d0d1a' },
        header: { background: '#0d0d1a', borderBottom: '1px solid #2d2d52' },
        body: { background: '#0d0d1a', padding: '16px 24px' },
      }}
    >
      {SECTIONS.map((section, idx) => (
        <div key={section.title}>
          {idx > 0 && <Divider style={{ borderColor: '#2d2d52', margin: '12px 0' }} />}
          <Title level={5} style={{ color: '#a8a8c0', marginTop: 0, marginBottom: 8, fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
            {section.title}
          </Title>
          {section.shortcuts.map((s, i) => (
            <ShortcutRow key={i} shortcut={s} />
          ))}
        </div>
      ))}
    </Modal>
  );
};

export default KeyboardShortcutsModal;
