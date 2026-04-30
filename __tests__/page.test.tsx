import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatPage from '../src/app/page'

// Mock fetch
global.fetch = jest.fn(() =>
    Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ reply: 'Test response from agent' }),
    })
) as jest.Mock;

describe('ChatPage Components', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        (global.fetch as jest.Mock).mockClear();
        // mock scrollIntoView
        window.HTMLElement.prototype.scrollIntoView = jest.fn()
    });

    it('renders the header correctly', () => {
        render(<ChatPage />)
        expect(screen.getByText('Meridian Electronics')).toBeInTheDocument()
        expect(screen.getByText('AI Customer Support')).toBeInTheDocument()
    })

    it('renders the welcome message initially', () => {
        render(<ChatPage />)
        expect(screen.getByText('Welcome to Meridian Support')).toBeInTheDocument()
    })

    it('sends a message when clicking a suggestion chip', () => {
        render(<ChatPage />)
        const browseChip = screen.getByText('Browse monitors')
        fireEvent.click(browseChip)

        // Welcome message should disappear, user message should appear
        expect(screen.queryByText('Welcome to Meridian Support')).not.toBeInTheDocument()
        expect(screen.getByText('Browse monitors')).toBeInTheDocument()

        // Should have called fetch
        expect(global.fetch).toHaveBeenCalledTimes(1)
    })

    it('allows typing and sending a custom message', () => {
        render(<ChatPage />)

        const input = screen.getByPlaceholderText('Type your message...')
        const sendButton = screen.getByText('Send')

        expect(sendButton).toBeDisabled()

        // Type in the box
        fireEvent.change(input, { target: { value: 'Hello Meridian' } })
        expect(sendButton).not.toBeDisabled()

        // Click send
        fireEvent.click(sendButton)

        // User message should appear
        expect(screen.getByText('Hello Meridian')).toBeInTheDocument()
        expect(global.fetch).toHaveBeenCalledTimes(1)
    })
})
