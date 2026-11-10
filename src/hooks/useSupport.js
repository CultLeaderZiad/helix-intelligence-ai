import { useCallback, useEffect, useRef, useState } from "react"
import { supportService } from "@/services"

export function useSupport() {
  const [tickets, setTickets] = useState([])
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [ticketDetails, setTicketDetails] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [isSendingReply, setIsSendingReply] = useState(false)
  const [errorCode, setErrorCode] = useState(null)
  const selectedTicketRef = useRef(selectedTicket)
  selectedTicketRef.current = selectedTicket

  const refreshTickets = useCallback(async () => {
    setIsLoading(true)
    setErrorCode(null)
    try {
      const response = await supportService.listTickets()
      const nextTickets = Array.isArray(response) ? response : []
      setTickets(nextTickets)
      if (!nextTickets.some((ticket) => ticket.id === selectedTicketRef.current)) {
        setSelectedTicket(nextTickets[0]?.id ?? null)
      }
      return nextTickets
    } catch {
      setErrorCode("loadTicketsFailed")
      return []
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshTickets()
  }, [refreshTickets])

  useEffect(() => {
    let active = true
    if (selectedTicket === null || selectedTicket === undefined) {
      setTicketDetails(null)
      setIsLoadingDetails(false)
      return () => { active = false }
    }

    setTicketDetails(null)
    setIsLoadingDetails(true)
    setErrorCode(null)
    supportService.getTicket(selectedTicket)
      .then((details) => { if (active) setTicketDetails(details) })
      .catch(() => { if (active) setErrorCode("loadTicketsFailed") })
      .finally(() => { if (active) setIsLoadingDetails(false) })

    return () => { active = false }
  }, [selectedTicket])

  const selectTicket = useCallback((ticketId) => {
    setErrorCode(null)
    setSelectedTicket(ticketId)
  }, [])

  const sendReply = useCallback(async (ticketId, message) => {
    const trimmedMessage = typeof message === "string" ? message.trim() : ""
    if (ticketId === null || ticketId === undefined || !trimmedMessage) {
      setErrorCode("replyEmpty")
      return null
    }

    setIsSendingReply(true)
    setErrorCode(null)
    try {
      const reply = await supportService.replyTicket(ticketId, trimmedMessage)
      setTicketDetails((previous) => {
        if (!previous || String(previous.id) !== String(ticketId) || !reply) return previous
        return {
          ...previous,
          replies: [...(Array.isArray(previous.replies) ? previous.replies : []), reply],
        }
      })
      return reply
    } catch {
      setErrorCode("replyFailed")
      return null
    } finally {
      setIsSendingReply(false)
    }
  }, [])

  return {
    tickets,
    selectedTicket,
    ticketDetails,
    isLoading,
    isLoadingDetails,
    isSendingReply,
    errorCode,
    refreshTickets,
    selectTicket,
    sendReply,
  }
}
