import React, { createContext, useContext, useState, useMemo } from 'react'

const InvestigationContext = createContext(null)

export function InvestigationProvider({ children }) {
  const [currentInvestigation, setCurrentInvestigation] = useState(null)

  const value = useMemo(() => ({
    currentInvestigation,
    setInvestigation: (addrOrObj) => {
      if (!addrOrObj) {
        setCurrentInvestigation(null)
      } else if (typeof addrOrObj === 'string') {
        setCurrentInvestigation({ address: addrOrObj })
      } else {
        setCurrentInvestigation(addrOrObj)
      }
    }
  }), [currentInvestigation])

  return (
    <InvestigationContext.Provider value={value}>
      {children}
    </InvestigationContext.Provider>
  )
}

export function useInvestigation() {
  const ctx = useContext(InvestigationContext)
  if (!ctx) throw new Error('useInvestigation must be used within InvestigationProvider')
  const { currentInvestigation, setInvestigation } = ctx
  return { currentInvestigation, setInvestigation }
}
